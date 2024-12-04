from pathlib import Path
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
from makemkv import MakeMKV, MakeMKVError
from datetime import datetime
from argparse import ArgumentParser
import itertools
import json
import logging
from enum import Enum
import sys

class Playlist:
    def __init__(self, TitleNum=-1, SourceFileName='', Description='', FileOutput='', Runtime='', Chapters=-1, Size=-1):
        self.TitleNum = TitleNum
        self.SourceFileName = SourceFileName
        self.Description = Description
        self.FileOutput = FileOutput
        self.Runtime = Runtime
        self.Chapters = Chapters
        self.Size = Size
    
    def __repr__(self):
        return f"Playlist(TitleNum={self.TitleNum}, SourceFileName={self.SourceFileName}, Description='{self.Description}', FileOutput='{self.FileOutput}', Runtime={self.Runtime}, Chapters={self.Chapters}, Size={self.Size})"
    
    def serialize(self):
        return {
            'TitleNum': self.TitleNum,
            'SourceFileName': self.SourceFileName,
            'Description': self.Description,
            'FileOutput': self.FileOutput,
            'Runtime': str(self.Runtime),
            'Chapters': self.Chapters,
            'Size': self.Size
        }
    
    @classmethod
    def deserialize(cls, data):
        # Convert Runtime string back to datetime.time if it's a valid time string
            
        return cls(
            TitleNum=data.get('TitleNum', -1),
            SourceFileName=data.get('SourceFileName', ''),
            Description=data.get('Description', ''),
            FileOutput=data.get('FileOutput', ''),
            Runtime = data.get('Runtime', ''),    
            Chapters=data.get('Chapters', -1),
            Size=data.get('Size', -1)
        )

class Movie:
    def __init__(self, Path, Title='', Size=-1, Processed=False, Playlists=None):
        self.Path = Path
        self.Title = Title
        self.Size = Size
        self.Processed = Processed
        self.Playlists = Playlists if Playlists is not None else []
    
    def __repr__(self):
        return f"Movie(Path='{self.Path}', Title='{self.Title}', Size={self.Size}, Processed={self.Processed}, Playlists={self.Playlists})"
    
    def serialize(self):
        return {
            'Path': str(self.Path),
            'Title': self.Title,
            'Size': self.Size,
            'Processed': self.Processed,
            'Playlists': [playlist.serialize() for playlist in self.Playlists]
        }
    
    @classmethod
    def deserialize(cls, data):
        # Deserialize nested Playlist objects
        playlists = [
            Playlist.deserialize(playlist_data)
            for playlist_data in data.get('Playlists', [])
        ]
        
        return cls(
            Path=data.get('Path', ''),
            Title=data.get('Title', ''),
            Size=data.get('Size', -1),
            Processed=data.get('Processed', False),
            Playlists=playlists
        )

def findMovieFiles(root: Path) -> list:
    movie_isos = [x for x in root.glob('**/*') if x.suffix == ".iso" or x.suffix == ".ISO"]
    # print(len(movie_isos))
    return movie_isos

def mkvProgress(task_description, progress, max):
    # print(f'{task_description}\t{progress}/{max}')
    # for progress in tqdm(range(max), desc=task_description):
    #     continue
    pass

def getBasicMovieFileDetails(file: Path) -> Movie:
    return Movie(Path=file, Size=file.stat().st_size)

def getMovieDetails(movie: Movie, min_length: int = 1200, size_cutoff: float = 0.5) -> Movie:
    print(f'Processing: {movie.Path}')
    try:
        mkv = MakeMKV(input=movie.Path, minlength=min_length)
        info = mkv.info(minlength=min_length)
    except MakeMKVError:
        print(f'ERROR, problem with {movie}.')
        pass
    except KeyboardInterrupt:
        mkv.kill()
    else:
        for idx, i in enumerate(info['titles']):
            if i.get('chapter_count') is None:
                continue
            if i['size'] > (movie.Size * size_cutoff):
                movie.Title = i['name'] if i.get('name') is not None else ''
                movie.Playlists.append(Playlist(TitleNum=idx, SourceFileName=i['source_filename'], Description=i['information'], FileOutput=i['file_output'], Runtime=i['length'], Chapters=i['chapter_count'], Size=i['size']))
    return movie

def getMovieListDetails(movies: list[Movie]):
    num_procs = cpu_count()
    result: list[Movie] = []
    
    with Pool(num_procs) as p:
        result = p.map(getMovieDetails, movies)

    # with Pool(num_procs) as p:
    #     result = list(tqdm(p.imap(getMovieDetails, movies), total=len(movies)))

    return result

def remuxMovie(movie: Movie, dest_root: Path, min_length:int=1200):
    movie_dir = Path(movie.Path).parent
    folder_name = movie_dir.name
    dest_path: Path = dest_root / folder_name

    if not dest_path.exists():
        Path.mkdir(dest_path)
    
    try:
        mkv = MakeMKV(input=movie.Path, minlength=min_length)
        mkv.mkv(movie.Playlists[0].TitleNum, dest_path)
    except KeyboardInterrupt:
        mkv.kill()
    finally:
        print('MakeMKV process killed.')

def remuxMovieList(movies: list[Movie], dest_root: Path, min_length: int=1200):    
    try:
        for m in tqdm(movies):
            if not m.Processed:
                print(f'Working on movie {m.Title}')
                remuxMovie(m, dest_root, min_length)
                m.Processed = True
    except KeyboardInterrupt:
        dumpMovieList(movies, 'in_process.json')
    finally:
        print(f'Program interrupted. Load in_process.json to continue.')

def dumpMovieList(movies: list, file: Path):
    with open(file, 'w') as f:
        json.dump([movie.serialize() for movie in movies], fp=f, indent=2)
    print('Saved list.')

def loadMovieList(file: Path) -> list[Movie]:
    with open(file, 'r') as f:
        movie_list = [m for m in json.load(f)]
    return [Movie.deserialize(movie_data) for movie_data in movie_list]

def checkDirExists(path:Path) -> bool:
    if not path.exists():
        return False
    
    return True

def getTitles(dir, json_out:Path):
    movies = [getBasicMovieFileDetails(movie) for directory in dir for movie in findMovieFiles(directory)]
    result = getMovieListDetails(movies)
    dumpMovieList(result, json_out)

def processMovies(movies_json, out_dir:Path):
    movies = loadMovieList(movies_json)
    remuxMovieList(movies)
    

# movies_e_details = list(map(lambda m: getBasicMovieFileDetails(m), findMovieFiles(Path('/mnt/e/Blu-ray/Movies'))))
# movies_f_details = list(map(lambda m: getBasicMovieFileDetails(m), findMovieFiles(Path('/mnt/f/Blu-ray/Movies'))))
# movies_g_details = list(map(lambda m: getBasicMovieFileDetails(m), findMovieFiles(Path('/mnt/g/Blu-ray/Movies'))))
# all_movie_details = [movies_e_details, movies_f_details, movies_g_details]

# for l in all_movie_details:
#     with Pool(4) as p:
#         result = p.map(getMovieDetails, l)

# has_mult_playlists = [m for m in result if len(m.Playlists) > 1]
# # dumpMovieList(result, 'movies_f.json')

# e = loadMovieList('movies.json')
# f = loadMovieList('movies_f.json')
# g = loadMovieList('movies_g.json')
# all_movies = e + f + g

# import operator
# original_size = sum([m.Size for m in g])
# mkv_size = sum([m.Playlists[0].Size for m in g])
# print(f'Current Size: {original_size / (1024**4)}\nResult Size: {mkv_size / (1024**4)}\nDifference: {(original_size - mkv_size) / (1024**4)}')


# dumpMovieList(all_movies, 'all_movies.josn')

# remuxMovieList(all_movies, Path('truenas/Movies'))

class ProgramAction(Enum):
    GET_TITLES = 0
    PROCESS_TITLES = 1,
    INVALID = 2

def setup_argument_parser():
    parser = ArgumentParser(description="Batch process ISO files to MKV.")
    group = parser.add_argument_group('Get Titles', 'Get Movie Titles')
    group.add_argument('--get_titles',
                       action='store_true',
                       help='Get titles from disk images found in paths provided by the in_dir argument.')
    group.add_argument('--in_dir', help='List of input directories (required when using --get_titles.)', 
                       type=Path, 
                       nargs='+')
    group.add_argument('--json', 
                        help='JSON file to save discovered movie titles to.', 
                        type=Path)
    group2 = parser.add_argument_group('Process Files', 'Remux movie files')
    group2.add_argument('--process', 
                       action='store_true',
                       help='Remux movies in loaded json file. Skips items marked as "Processed".')
    group2.add_argument('--filter', 
                       type=str,
                       nargs='+',
                       help='Process movie(s) provided in list')
    group2.add_argument('--load_json', help='Load json file created with the --json argument.', 
                        type=Path)
    group2.add_argument('--out_dir', 
                        help='Root directory where MKV files will be saved.', 
                        type=Path)

    return parser

def validate_args(args) -> ProgramAction:
    action: ProgramAction = ProgramAction.INVALID
    if args.get_titles:
        if not args.in_dir:
            sys.exit("Error: --in_dir is required when using --get_titles")
        if args.in_dir:
            for d in args.in_dir:
                if not checkDirExists(d):
                    sys.exit(f'Error: Invalid directory. {d}')
        if not args.json:
            sys.exit("Error: --json output path is required when using --get_titles")
        action = ProgramAction.GET_TITLES    
    
    if args.process:
        if not args.load_json:
            sys.exit("Error: --load is required when using --process")
        if args.load_json:
            if not checkDirExists(args.load_json):
                sys.exit(f'Error: Invalid directory. {args.load_json}')
        if not args.out_dir:
            sys.exit("Error: --out_dir is required when using --process")
        if args.out_dir:
            if not checkDirExists(args.out_dir):
                sys.exit(f'Error: Invalid directory. {args.out_dir}')
        action = ProgramAction.PROCESS_TITLES
    
    return action

    
def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.CRITICAL)

    parser = setup_argument_parser()
    args = parser.parse_args()
    action = validate_args(args)

    # in_dirs: list[Path] = args.in_dir if args.in_dir is not None else []
    # our_dir: Path = args.out_dir if args.out_dir is not None else Path()
    # json_out: Path = args.json if args.json is not None else Path()
    # json_in: Path = args.load_json if args.load_json is not None else Path()
    # filter: list[str] = args.filter if args.filter is not None else list[str]

    # print(in_dirs)
    # print(our_dir)
    # print(json_out)
    # print(json_in)
    # print(filter)

    match(action):
        case ProgramAction.GET_TITLES:
            getTitles(args.in_dir, args.json)
        case ProgramAction.PROCESS_TITLES:
            print(args.load_json, args.out_dir)

if __name__ == "__main__":
    main()

