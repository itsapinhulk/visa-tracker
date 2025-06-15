# Visa Tracker


# Downloading Data

There are two parts to the data - cache of web pages and the computed CSV files, with the
latter being stored in the repo itself. To update it run -

```
python -m src.downloader.download --cache_dir ./cache --data_dir ./data
```
