import os
from datetime import date
from urllib.parse import urlparse
from page_analyzer.parser import parse_response
import requests
import requests.exceptions
import validators
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    get_flashed_messages,
    redirect,
    render_template,
    request,
    url_for,
)

from page_analyzer.repositories import Checks, Urls

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
database_url = os.getenv('DATABASE_URL')





@app.route('/')
def index():
    url = {}
    return render_template(
        'index.html',
        url=url
    )


@app.route('/urls')
def urls_index():
    checks_repo = Checks(database_url)
    urls = checks_repo.get_url_with_last_check()
    return render_template(
        'urls.html',
        urls=urls,
    )


@app.route('/urls', methods=['POST'])
def index_post():
    urls_repo = Urls(database_url)

    url = request.form.to_dict().get('url')
    is_valid = validators.url(url)

    if not is_valid:
        flash('Некорректный URL', 'danger')
        return render_template('index.html', url=url), 422

    parsed_url = urlparse(url)
    name = f'{parsed_url.scheme}://{parsed_url.netloc}'
    created_at = date.today().isoformat()
    url = {
        'name': name,
        'created_at': created_at
    }
    url, status = urls_repo.save(url)
    if status == 'success':
        flash('Страница успешно добавлена', 'success')
    elif status == 'exist':
        flash('Страница уже существует', 'info')

    return redirect(url_for('urls_show', url_id=url['id']))


@app.route('/urls/<url_id>')
def urls_show(url_id):
    urls_repo = Urls(database_url)
    checks_repo = Checks(database_url)
    url = urls_repo.find(url_id)
    checks = checks_repo.get_checks(url_id)
    return render_template(
        'show.html',
        url=url,
        checks=checks
    )


@app.route('/urls/<url_id>/checks', methods=['POST'])
def url_check(url_id):
    urls_repo = Urls(database_url)
    checks_repo = Checks(database_url)
    url = urls_repo.find(url_id)

    try:
        response = requests.get(url['name'])
        response.raise_for_status()
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError
    ):
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('urls_show', url_id=url_id))
    else:
        tags = parse_response(response)
        check = {
            'url_id': url_id,
            'code': response.status_code,
            'h1': tags.get('h1', ''),
            'title': tags.get('title', ''),
            'description': tags.get('description', ''),
            'created_at': date.today().isoformat()
        }
        checks_repo.save(check)
        flash('Страница успешно проверена', 'success')
        return redirect(url_for('urls_show', url_id=url_id))
