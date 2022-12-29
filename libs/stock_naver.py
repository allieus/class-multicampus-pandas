import datetime
import pandas as pd
import requests
import time
import xlwings as xw
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from .utils import percent_to_float


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36'
    ),
}


def get_국내증시_검색상위(field_id_list=None):
    if field_id_list is None:
        field_id_list = ["quant", "open_val",
                         "high_val", "low_val", "per", "roe"]

    url = "https://finance.naver.com/sise/field_submit.nhn"
    params = {
        "menu": "lastsearch2",
        "returnUrl": "http://finance.naver.com/sise/lastsearch2.nhn",
        "fieldIds": field_id_list,
    }

    res = requests.get(url, headers=HEADERS, params=params)
    html = res.text

    df = pd.read_html(html, header=0)[1]
    df = df.dropna().drop(['순위'], axis="columns").set_index('종목명')
    df['검색비율'] = percent_to_float(df['검색비율'])
    df['등락률'] = percent_to_float(df['등락률'])

    return df


def get_실시간_국내증시_인기검색종목():
    sise_url = 'https://finance.naver.com/sise/'

    res = requests.get(sise_url, headers=HEADERS)
    res.raise_for_status()
    html = res.text
    soup = BeautifulSoup(html, 'html.parser')

    item_list = []

    for tag in soup.select('#popularItemList li'):
        name_tag = tag.select_one('a')
        url = urljoin(sise_url, name_tag['href'])
        code = parse_qs(urlparse(url).query)['code'][0]
        name = name_tag.text.strip()
        value_tag = tag.select_one('.up, .dn, .noc')
        direction = ' '.join(value_tag['class'])
        value = int(value_tag.text.replace(',', ''))
        item_list.append({
            '종목명': name,
            '종목코드': code,
            'direction': direction,
            '거래가': value,
            'url': url,
        })

    df = pd.DataFrame(item_list).set_index('종목명')

    return df


def get_종목별_일별_거래량(code, max_page=3):
    '60일치 거래량 데이터 크롤링'

    for page in range(1, max_page+1):  # 페이지당 20개 * 3페이지
        params = {
            'code': code,
            'page': page,
        }
        res = requests.get(
            "https://finance.naver.com/item/frgn.nhn", headers=HEADERS, params=params)
        html = res.text

        df = pd.read_html(html)[2].dropna(how='all')
        df.columns = [
            '날짜', '종가', '전일비', '등락률', '거래량',
            '기관 - 순매매량', '외국인 - 순매매량', '외국인 - 보유주수', '외국인 - 보유율(%)',
        ]
        df = df.iloc[2:].set_index('날짜')
        df.index = pd.to_datetime(df.index)

        df['종가'] = df['종가'].astype('float')
        df['전일비'] = df['전일비'].astype('float')
        df['거래량'] = df['거래량'].astype('float')

        df['등락률'] = percent_to_float(df['등락률'])
        df['외국인 - 보유율(%)'] = percent_to_float(df['외국인 - 보유율(%)'])
        df['기관 - 순매매량'] = df['기관 - 순매매량'].apply(
            lambda s: float(s.replace(',', '')))
        df['외국인 - 순매매량'] = df['외국인 - 순매매량'].apply(
            lambda s: float(s.replace(',', '')))

        yield df

        time.sleep(0.1)


def get_주가시장별_시간별_시세(code, max_page=100):
    url = "https://finance.naver.com/sise/sise_index_time.nhn"
    return get_시간별_시세(code, url, max_page)


def get_종목별_시간별_시세(code, max_page=100):
    url = "https://finance.naver.com/item/sise_time.nhn"
    return get_시간별_시세(code, url, max_page)


def get_시간별_시세(code, url, max_page=100):
    now = datetime.datetime.now()
    if now.hour < 9:
        now = now.replace(hour=0, minute=0, second=0,
                          microsecond=0) - datetime.timedelta(seconds=1)

    thistime = now.strftime('%Y%m%d%H%M00')

    df_list = []
    last_df = None

    for page in range(1, max_page+1):
        params = {
            "code": code,
            "thistime": thistime,
            "page": page,
        }

        res = requests.get(url, headers=HEADERS, params=params)
        html = res.text
        page_df = pd.read_html(html, header=0)[0].dropna()

        def apply_fn(t):
            hour, minute = map(int, t.split(':'))
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        page_df['체결시각'] = page_df['체결시각'].apply(apply_fn)
        page_df = page_df.set_index('체결시각')

        if last_df is not None:
            is_over_page = last_df.index.equals(page_df.index)
            if is_over_page:
                break

        last_df = page_df

        df_list.append(page_df)
        if page_df.empty:
            break

    return pd.concat(df_list)


def get_kospi200(code, max_page=1):
    last_df = None

    for page in range(1, max_page+1):
        params = {
            'code': code,
            'page': page,
        }
        res = requests.get(
            "https://finance.naver.com/sise/sise_index_day.nhn", headers=HEADERS, params=params)
        res.raise_for_status()
        html = res.text

        current_df = pd.read_html(html, header=0)[0]
        current_df = current_df.dropna().set_index('날짜')
        current_df.index = pd.to_datetime(current_df.index)

        if last_df is not None:
            is_over_page = last_df.index.equals(current_df.index)
            if is_over_page:
                break

        last_df = current_df

        yield current_df

        time.sleep(0.1)
