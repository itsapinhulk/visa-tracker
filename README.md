# Visa Tracker


## Downloading Data

There are two parts to the data - cache of web pages and the computed CSV files, with the
latter being stored in the repo itself. To update it run the following command -

```
python -m src.downloader.download --cache_dir ./cache --data_dir ./data
```

or on Unix

```
./update_data.sh
```

## Web Server

The NPM / React based web server lives in the `src/web` directory. To run it, run the following
command -

```
cd src/web
npm start
```
