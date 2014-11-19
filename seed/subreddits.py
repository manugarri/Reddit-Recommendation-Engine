'''get a list of all subredits'''
import requests
import json
import time

def add_subs(content, count):
    if content:
        for sub in content.get('data').get('children'):
            line = sub.get('data').get('display_name')
            file.write(line)
            file.write('\n')
        block_count = len(content.get('data').get('children'))
    return block_count

def get_url(url):
    while 1:
        try:
            content = requests.get(url, timeout=5)
            content = json.loads(content.content)
            return content
        except:
            time.sleep(60)


subs = []
url = 'http://www.reddit.com/reddits.json'
file = open('subs.txt', 'w')
content = get_url(url)
subs = add_subs(content, subs)

base_url = 'http://www.reddit.com/reddits.json?count={0}&after={1}'
count=0
while 1:
    if content:
        after = content.get('data').get('after')
        if after:
            url = base_url.format(count, after)
            print url
            content = get_url(url)
            count += add_subs(content, count)
    else:
        break
file.close()
with open('subs.json', 'w') as file:
    json.dump(subs, file)
    file.close()
