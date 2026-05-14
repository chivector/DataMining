$env:DF_API_URL="http://123.129.219.111:3000/v1"  
$env:DF_API_KEY="your-df-api-key" 
python scripts/collect_experiment_responses.py --provider df --workers 12  --log-every 5 --flush-every 5
