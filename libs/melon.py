import requests
import pandas as pd
from bs4 import BeautifulSoup


def 멜론차트_가져오기():
    # 멜론 차트 페이지의 HTML 응답 문자열을 획득합니다.
    url = 'http://www.melon.com/chart/index.htm'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
    }
    html = requests.get(url, headers=headers).text

    # HTML 응답 문자열로부터, 필요한 태그 정보를 추출하기 위해, BeautifulSoup4 객체를 생성합니다.
    soup = BeautifulSoup(html, 'html.parser')

    # BeautifulSoup4 객체를 통해 노래 정보를 추출해냅니다.
    song_list = []

    for song_tag in soup.select('#tb_list tbody tr'):
        곡일련번호 = song_tag['data-song-no']
        커버이미지_주소 = song_tag.select_one('img')['src']
        곡명 = song_tag.select_one('a[href*=playSong]').text
        가수 = song_tag.select_one('a[href*=goArtistDetail]').text
        앨범 = song_tag.select_one('a[href*=goAlbumDetail]')['title']
        순위 = song_tag.select_one('.rank').text

        song = {
            '곡일련번호': 곡일련번호,
            '순위': 순위,
            '곡명': 곡명,
            '가수': 가수,
            '앨범': 앨범,
            '커버이미지_주소': 커버이미지_주소,
        }
        # print(song)

        song_list.append(song)

    # 추출해낸 곡 정보를 Pandas의 DataFrame화 시킵니다.
    song_df = pd.DataFrame(song_list, columns=['순위', '곡일련번호', '앨범', '곡명', '가수', '커버이미지_주소']).set_index('곡일련번호')

    # song_df의 인덱스가 노래 id 목록입니다.
    song_id_list = song_df.index

    # 노래별 "좋아요" 정보는 별도로 요청해야합니다. 노래 id 목록을 인자로 넘겨서 좋아요 정보를 획득합니다.
    url = 'http://www.melon.com/commonlike/getSongLike.json'
    params = {
        'contsIds': song_id_list,
    }
    result = requests.get(url, headers=headers, params=params).json()
    like_dict = { str(song['CONTSID']):song['SUMMCNT'] for song in result['contsLike'] }

    # 좋아요 정보를 song_df에 새로운 필드로 추가합니다.
    song_df['좋아요'] = pd.Series(like_dict)

    return song_df
