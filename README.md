# AutoRemux

AutoRemux aims to make the process of batch-converting ISO images to MKV easy.

## Description

AutoRemux uses MakeMKV to batch process folders containing ISO images and outputting MKV files to a destination folder. There are two steps to this process:
## Finding Main Titles
Each ISO file will be passed to MakeMKV to (hopefully) find the main title. The methodology used is very rudamentary, generally searching for the largest playlist.
Once this process is complete, a json file will be written to disk. This file contains information found about each movie and includes the title that will be saved.
This title can be changed manually if needed, if the wrong title has been identified.

This script assumes ISOs are kept in a folder structure like so: <Root>/Movies/Movie Name (Year)/Movie.iso
MKV output will match this folder structure: <Outdir>/Movie Name (Year)/title.mkv

## Processing the Queue
Once the queue json file has been created, run the program with the json file as an input. Each movie will be converted in turn.

## Getting Started


### Dependencies

* makemkv (pip install makemkv)
* tqdm

### Executing program
#### Get Titles
```
python AutoRemux.py --get-titles --in-dir <root movie dir> --json movie_queue.json
```
#### Process Titles
```
python AutoRemux.py --process --load-json movie_queue.json --out-dir <root output dir>
```
