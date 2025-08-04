import requests
from bs4 import BeautifulSoup

# Example function to use third-party for Facebook


def download_fb_video_using_service(url):
    api_url = 'https://fbdownloader.net/download'

    payload = {'video': url}
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        print(f"Requesting third-party service for {url}")
        response = requests.post(api_url, data=payload, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            download_div = soup.find('div', {'class': 'download'})
            
            if download_div:
                video_link = download_div.find('a').get('href')
                print(f"Download link found: {video_link}")
                return video_link
            else:
                print("No downloadable link found.")
        else:
            print(f"Failed request with status: {response.status_code}")
    except Exception as e:
        print(f"Error while fetching video: {e}")

    return None

print(download_fb_video_using_service('https://www.facebook.com/facebook/videos/10153231379946729/'))
