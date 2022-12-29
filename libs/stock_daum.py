import time
import requests
import pandas as pd


def get_us_sp500(max_page=100):
    for page in range(1, max_page+1):
        params = {
            'symbolCode': 'US.SP500',
            'pagination': 'true',
            'page': page,
            'perPage': 100,
        }

        headers = {
            'Referer': 'http://finance.daum.net/global/quotes/US.SP500',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        }

        url = 'http://finance.daum.net/api/quote/US.SP500/days'
        
        res = requests.get(url, params=params, headers=headers)
        res.raise_for_status()
        response_obj = res.json()

        df = pd.DataFrame(response_obj['data'])
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df.set_index('date')

        yield df
        
        if page >= response_obj['totalPages']:
            break
        
        time.sleep(0.1)
