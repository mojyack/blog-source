import sys
import os
import glob
import shutil

packages_path = os.path.join(os.path.dirname(__file__), ".packages")
if os.path.isdir(packages_path):
    sys.path.append(packages_path)

import toml
import markdown
import tinyhtml
from tinyhtml import h as htag

def build_page(title, body, css):
    return tinyhtml.html(lang='jp')(
                htag('title')(title),
                htag('head')(
                    htag('meta', content='text/html;charset=utf-8', http_equiv='Content-Type'),
                    htag('link', rel='stylesheet', href='/blog/assets/style.css'),
                    htag('link', rel='stylesheet', href='/blog/assets/' + css),
                ),
                htag('header')(
                    htag('div' , klass='title')(
                        htag('h1')('dn1(mojyack\'s blog)'),
                        htag('h2')('猫と仲良く暮らしたいだけの男、プログラマの成り損ない。'),
                    ),
                    htag('nav', klass='main_menu')(
                        htag('a', href='/blog/')("Home"),
                        htag('a', href='/blog/categories/index.html')("Categories"),
                        htag('a', href='/blog/about.html')("About"),
                    ),
               ),
               tinyhtml.raw(body),
           )

def compile_article(path):
    fixed_path = path.replace(' ', '_')
    output_dir = 'blog/' + fixed_path

    os.makedirs(output_dir, exist_ok=True)

    info = toml.load(f'{path}/info.toml')
    date = os.path.basename(path)[:10]
    body = htag('div', id='article_header')(
        htag('h1', id='article_title')(info['title']),
        htag('div', id='article_date')(date),
        htag('ul', id='tag_list')(
            (htag('li')(htag('a', href=f'/blog/categories/{tag}.html')(tag)) for tag in info['tag']),
        ),
    ).render()
    for file in info['files']:
        article_path = f'{path}/{file}'
        body += markdown.markdown(open(article_path).read(), extensions=['fenced_code', 'tables'])

    index = build_page(info['title'], body, 'article.css').render()

    open(f'{output_dir}/index.html', mode='w').write(index)

    for data in info['data']:
        shutil.copytree(f'{path}/{data}', f'{output_dir}/{data}', dirs_exist_ok=True)

    result = {}
    result['title'] = info['title']
    result['description'] = info['description']
    result['link'] = fixed_path + '/index.html'
    result['date'] = date
    result['tags'] = info['tag']
    return result

def main():
    texts = {}

    for file in sorted(glob.glob(os.path.join("articles", "*")), reverse=True):
        if not os.path.isdir(file):
            continue

        article = compile_article(file)

        text = htag('article', klass='article')(
                    htag('a', href = '/blog/' + article['link'])(
                        htag('h1', id='article_title')(article['title']),
                    ),
                    htag('div', id='article_date')(article['date']),
                    htag('ul', id='tag_list')(
                        (htag('li')(htag('a', href=f'/blog/categories/{tag}.html')(tag)) for tag in article['tags']),
                    ),
                    htag('p')(article['description']),
                ).render()

        for t in article['tags'] + ['index']:
            if not t in texts:
                texts[t] = [0, '' if t == 'index' else htag('h1')(f'Articles tagged with "{t}"').render()]

            texts[t][0] += 1
            texts[t][1] += text
        
    os.makedirs('blog/categories', exist_ok=True)
    categories_index_elements = ''
    for tag in sorted(texts):
        if tag == 'index':
            index = build_page('dn1', texts[tag][1], 'index.css').render()
            open('blog/index.html', mode='w').write(index)
        else:
            index = build_page(f'tag: "{tag}"', texts[tag][1], 'index.css').render()
            open(f'blog/categories/{tag}.html', mode='w').write(index)
            categories_index_elements += htag('li')(
                htag('a', href=f'/blog/categories/{tag}.html')(f'{tag} ({texts[tag][0]})'),
            ).render()

    categories_index_body = htag('ul', klass='category_list')(tinyhtml.raw(categories_index_elements)).render()
    categories_index = build_page('Categories', categories_index_body, 'categories.css').render();
    open('blog/categories/index.html', mode='w').write(categories_index)

    about_body = htag('div', klass='article_title')(
        htag('h1')('About me'),
    ).render() + markdown.markdown(open('about.md').read())
    about = build_page('About', about_body, 'article.css').render();
    open('blog/about.html', mode='w').write(about)

    shutil.copytree(f'assets', f'blog/assets', dirs_exist_ok=True)

main()
