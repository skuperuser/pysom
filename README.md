# pysom
A python library for somtoday to get grades, homework, schedules, news, absences, etc. 
Scrapes the somtoday site for data to avoid the constantly changing authentication mess regarding the somtoday api.
Uses the `requests` module for scraping. Only requires a browser for login.

## Usage:

### Import
```python
from pysom import pysom
```

### Usage

`sso_login()` - opens a gecko (firefox) webbrowser to get auth cookies from somtoday. If this is not in your script, you will be prompted for login when using another function (like the ones below). why it's named sso_login? no idea.

`get_news()` - returns a **list** of news from https://elo.somtoday.nl/home/news.

`get_subject_docentenlijst()` - returns a **dict** containing all of a students subjects and who teaches these.

`get_persoonsgegevens()` - returns a **dict** of the student's information (birthday, (user)name, nationality, etc)

`get_grades_for_all_subjects()` - returns a **dict** containing the average grade for _all_ subjects of the student.

the rest (`get_schedule(), get_docentenlijst(), get_subjects(), get_school_name(), get_grade_for_subject()` + many more) is self-explanitory.

**NOT** affiliated with somtoday in any way. use responsibly.
