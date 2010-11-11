logfile_rotating_size = 100000 
log_to_stdout = 1
log_to_file = 0 
web_history = 10000 
minimum_interval = 60 
log_format = "" 
max_retries = 1 
retry_delay = 60 
logfile = "das_analytics.log" 
logfile_rotating_interval = 24 
no_start_offset = False 
web = True 
web_port = 8213 
logfile_mode = "None" 
workers = 4
log_to_stderr = 0 
web_base = "/analytics" 
logfile_rotating_count = 0

Task("DatasetHotspot", "ValueHotspot", 3600, key="dataset.name")
Task("BlockHotspot", "ValueHotspot", 3600, key="block.name")
Task("FileHotspot", "ValueHotspot", 3600, key="file.name")
Task("SiteHotspot", "ValueHotspot", 3600, key="site.name")
Task("RunHotspot", "ValueHotspot", 3600, key="run.run_number")
