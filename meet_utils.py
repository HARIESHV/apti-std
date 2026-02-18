import requests
from bs4 import BeautifulSoup
import re

def get_meet_info(url):
    """
    Attempts to fetch basic info from a Google Meet link.
    Returns a dictionary with 'title' and 'status'.
    """
    if not url:
        return {"title": "No Link", "status": "Inactive"}

    # Extract meeting ID as fallback
    meeting_id = "Unknown"
    match = re.search(r'meet\.google\.com/([a-z0-9-]+)', url)
    if match:
        meeting_id = match.group(1)
    elif "meet.new" in url:
        meeting_id = "New Meeting"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        # We use a session for potential redirects and cookies
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=8, allow_redirects=True)
        
        if response.status_code != 200:
            return {"title": f"Meeting {meeting_id} (Code {response.status_code})", "status": "Inaccessible"}

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Google Meet page title usually contains the meeting name or ID
        title_tag = soup.find('title')
        title = title_tag.text if title_tag else f"Meeting {meeting_id}"
        
        # Clean up title (remove "Google Meet" suffix)
        title = title.replace(" - Google Meet", "").replace("Google Meet", "").strip()
        
        if not title or title.lower() == "google meet":
            title = f"Meeting {meeting_id}"
        
        # Look for indicators of an active meeting
        # Since modern Google Meet is JS-heavy, we look for specific breadcrumbs
        is_active = any(word in response.text.lower() for word in ["join", "asking to join", "ready to join"])
        
        return {
            "title": title,
            "status": "Online" if is_active else "Offline"
        }
    except requests.exceptions.Timeout:
        return {"title": f"Meeting {meeting_id} (Timeout)", "status": "Unknown"}
    except requests.exceptions.ConnectionError:
        return {"title": f"Meeting {meeting_id} (Connection Error)", "status": "Offline"}
    except Exception as e:
        print(f"Scraping error: {e}")
        return {"title": f"Meeting {meeting_id} (Scrape Failed)", "status": "Unknown"}

if __name__ == "__main__":
    # Test
    test_url = "https://meet.google.com/abc-defg-hij"
    print(get_meet_info(test_url))
