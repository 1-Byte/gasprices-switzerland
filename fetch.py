import bs4
import csv
import json
import re
import requests_cache
import sys


CATEGORIES = ['Typ II', 'Typ III', 'Typ IV', 'Typ V', 'Typ VI', 'Typ VII', 'Typ VIII', 'Typ IX', 'Typ X']
REGIONS = ['Ost', 'West', 'Zentral', 'GR', 'VS', 'TI', 'BE', 'AG/ZH/SH', 'BS/BL/SO/JU']

session = requests_cache.CachedSession(allowable_methods=('GET', 'POST'),allowable_codes=(200, 403, 404, 500))


def post_soup(url, **kwargs):
    res = session.post(url, **kwargs)
    res.raise_for_status()
    return bs4.BeautifulSoup(res.content, 'lxml')


def fetch_single(cat, bfs, provider):
    soup = post_soup('http://gaspreise.preisueberwacher.ch/web/index.asp', params={'z': 5, 'codeort': bfs, 'codelieferant': provider, 'codekategorie': cat})
    for td in soup.find_all('td'):
        if td.text == 'Ihr Gaspreis:':
            m = re.search(r'(\d+\.\d+) Rp', td.parent.text)
            assert m
            return m.group(1)
    assert False


def fetch_multi(cat, bfs):
    soup = post_soup('http://gaspreise.preisueberwacher.ch/web/index.asp', params={'z': 3, 'codeort': bfs})
    results = []
    for a in soup.find_all('a'):
        m = re.search('codelieferant=(\d+)', a['href'])
        if not m: continue
        provider = int(m.group(1))
        results.append([a.text.replace('\n', '').strip(), fetch_single(cat, bfs, provider)])
    return results


def fetch_map(cat, reg):
    soup = post_soup('http://gaspreise.preisueberwacher.ch/web/resource/control/content/d/contentPopup_schweiz1.asp', data={'codekategorie': cat, 'gebiet': reg})
    results = {}
    for a in soup.find_all('area'):
        m = re.search(r'\((\d+)\)', a['onclick'])
        assert m
        bfs = int(m.group(1))
        row = json.loads('[' + a['onmouseover'][3:-2].replace("'", '"') + ']')
        assert len(row) == 7
        municipality = row[0].strip()
        if int(row[2]) == 1:
            results[bfs] = [[cat, bfs, municipality, row[1].strip(), row[4]]]
        elif bfs not in results:
            results[bfs] = [[cat, bfs, municipality] + r for r in fetch_multi(cat, bfs)]
    return results


def main(args):
    writer = csv.writer(sys.stdout)
    writer.writerow(['category', 'bfs', 'municipality', 'provider', 'price'])
    for c in CATEGORIES:
        for r in REGIONS:
            results = fetch_map(c, r)
            for rows in results.values():
                writer.writerows(rows)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
