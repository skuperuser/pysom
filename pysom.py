from os import error, remove
import selenium.webdriver 
from bs4 import BeautifulSoup
from time import sleep
import json
import requests
import re
import datetime

class Auth:
    def __init__(self, is_invalid=False) -> None:
        self.is_invalid = is_invalid

        try:
            with open('creds.json', 'r') as file:
                self.data = json.load(file)
        except:
            pass
            #print("Not logged in!")
        
        if self.is_invalid == True:
            self.data = None

    def sso_login(self, force=False, verbose=True):
        try:
            if self.data and not force == True:
                return self.data['jsessionid']['value'], self.data['token']['value']
        
        except:
            pass

        if verbose:
            print('Prompting for login...')
        driver = selenium.webdriver.Firefox()
        driver.get("https://inloggen.somtoday.nl")
        while True:
            jsessionid = driver.get_cookie("JSESSIONID")
            token = driver.get_cookie('production-sis-elo-stickiness')
            if token:
                driver.close()
                with open('creds.json', 'w') as file:
                    json.dump({'jsessionid': jsessionid, 'token': token}, file)
                return jsessionid['value'], token['value']
            sleep(1)

class Main(Auth):
    def __init__(self) -> None:
        self.token = ""
        self.jsessionid = ""
        self.refresh_creds()
    
    def refresh_creds(self):
        try:
            with open('creds.json', 'r') as file:
                self.data = json.load(file)
            self.token = self.data['token']['value']
            self.jsessionid = self.data['jsessionid']['value']
        except:
            #print("Not logged in!")
            self.sso_login(force=True) # don't force this
    
    def make_request(self, page): # baseurl = elo.somtoday.nl
        ### HACK FIX ### avoid a bug triggering an infinite auth loop
        try:
            with open('creds.json', 'r') as file:
                self.data = json.load(file)
            self.token = self.data['token']['value']
            self.jsessionid = self.data['jsessionid']['value']
        except:
            self.sso_login(force=True)
        ######
        headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/jxl,image/webp,*/*;q=0.8','Accept-Language': 'en-US,en;q=0.5','Accept-Encoding': 'gzip, deflate, br','Dnt': '1','Upgrade-Insecure-Requests': '1','Sec-Fetch-Dest': 'document','Sec-Fetch-Mode': 'navigate','Sec-Fetch-Site': 'none','Sec-Fetch-User': '?1','Te': 'trailers',
        }

        cookies = {
        'JSESSIONID': self.jsessionid,'production-sis-elo-stickiness': f'{self.token}','historyAPIAvailable': 'true',
        }
        try:
            
            response = requests.get(f'https://elo.somtoday.nl{page}', headers=headers, cookies=cookies, allow_redirects=True)
        except requests.TooManyRedirects:
            self.sso_login(force=True)
            self.refresh_creds()
            self.make_request(page) # redo request  
        if response.url.startswith("in"):
            self.sso_login(force=True)
            self.refresh_creds()
            self.make_request(page) # redo request
        return response

    def get_news(self, windowsize=800):
        newslist = []
        r = self.make_request(f'/home/news?windowsize={windowsize}') # windowsize= hoeveel in 1 keer te laten zien
        soup = BeautifulSoup(r.text, "html.parser")
        print(soup.prettify())
        text_only = soup.get_text()

        #items = text_only.split('\n\n\n\n\n\n\n')
        pattern = re.compile(r'[a-zA-Z]{2}\d{1,2}[a-zA-Z]{3}\.?')

        items = pattern.split(text_only)

        
        for i in items:
            if i == '\n\nToon meer dagen':
                pass
            elif i == '\n\n\n\n\n\nRooster':
                pass
            else:
                i = i.replace('\n\n\n', '\n')
                i = i.replace('\n\n', '\n')
                newslist.append(i)
        
        newslist2 = []
        for n in newslist:
            n = n.split('\n\n')
            for i in n:
                newslist2.append(i)

        newslist3 = []
        for n in newslist2:
            if n != "" and n != "\n" and n != '\n\n':
                newslist3.append(n)
        
        newslist4 = []
        for n in newslist3:
            if n != 'Rooster' and n != 'Toon meer dagen' and n != 'nieuws' and n != 'rooster' and n != 'huiswerk' and n != 'cijfers' and n != 'vakken' and n != 'afwezigheid' and n != 'leermiddelen' and n != '\nGetoond:' and n != 'Nieuws\n' and not n.startswith('versie 1') and n != '\nnieuws' and n != '\nSomtoday - Samen Slimmer Onderwijs':
                newslist4.append(n)
        
        #for i in newslist4:
        #    print('---\n'+i)
        return newslist4

    def get_persoonsgegevens(self):
        soup = BeautifulSoup(self.make_request('/home/profile').content, 'html.parser')
        labels = soup.find_all(class_='label')
        values = soup.find_all(class_='twopartfields')

        data_list = []
        for label, value in zip(labels, values):
            label_text = label.get_text(strip=True)
            value_text = value.get_text(strip=True)
            data_list.append(label_text)
            data_list.append(value_text)
        #print(data_list)
        s = 0
        for i in data_list:
            #print(i, " ", s, '\n')
            s += 1

        if data_list[51].startswith('[em'): # HACK: prevent returning email as school name for migrants
            data_list[51] = data_list[55]

        to_return = { # TODO: implement Stamgroep, Mentor, Schoolloopbaan.
            'username': data_list[3],
            'name': data_list[7],
            'date_of_birth': data_list[15],
            'nationality': data_list[19],
            'address': data_list[27],
            'postal_code': data_list[31],
            'country': data_list[35],
            'school_name': data_list[51], 
        }
        return to_return

    def get_docentenlijst(self, include_none=False):
        r = self.make_request('/home/subjects')
        soup = BeautifulSoup(r.content, 'html.parser')
        docenten_html = soup.find_all(class_='r-content sub')
        soup2 = BeautifulSoup(str(docenten_html), 'html.parser')
        docenten = soup2.getText()
        docenten = docenten.replace(',', '')
        docenten = str(docenten)
        docenten = docenten.replace('[', "")
        docenten = docenten.replace(']', "")
        docenten = docenten.split('\n\n')

        docentenlijst = []
        for d in docenten:
            d = d.replace('\n', '')
            if d.startswith(" "):
                d = d[1:]
            
            if include_none == False:
                if not d != "" or not d != " " or not d != "  ":
                    continue
            
            docentenlijst.append(d)
        return docentenlijst

    def get_subjects(self):
        soup = BeautifulSoup(self.make_request('/home/subjects').content, 'html.parser')
        html_subject_list = soup.find_all('h2')
        #print(html_subject_list)
        string = str(html_subject_list)
        #print(string)
        string = string.replace('<h2>', '')
        string = string.replace('</h2>', '')
        string = string.replace('[', '')
        string = string.replace(']', '')
        string = string.lower()
        string = string.split(', ')

        compat_list = []
        for i in string:
            i = i.replace(' ', '_')
            compat_list.append(i)

        return compat_list
    
    def get_subject_docentenlijst(self):
        docenten = self.get_docentenlijst(include_none=True)
        subjects = self.get_subjects()
        dictionary = {}
        for i in enumerate(subjects):
            i = i[0]

            dictionary[subjects[i].replace(' ', '_')] = docenten[i]
        return dictionary

    def get_address(self):
        return {'address':self.get_persoonsgegevens()['address'], 'postal_code':self.get_persoonsgegevens()['postal_code']}
    def get_date_of_birth(self):
        return {'date_of_birth': self.get_persoonsgegevens()['date_of_birth']}
    def get_full_name(self):
        return {'full_name': self.get_persoonsgegevens()['name']}
    def get_school_name(self):
        return {'school_name': self.get_persoonsgegevens()['school_name']}
    def get_username(self):
        return {'username': self.get_persoonsgegevens()['username']}

    def get_grade_for_subject(self, subject): # returns average grade (for now)
        subject = subject.lower()
        subject = subject.replace(' ', '_')
        available_subjects = self.get_subjects()
        if subject not in available_subjects:
            raise ValueError("You don't have that subject. :( Print `get_subjects()` to see all subjects available to you.")
        
        soup = BeautifulSoup(self.make_request('/home/grades').content, 'html.parser')
        rs = soup.find_all(class_='m-element')
        
        pattern = r'href="https://elo\.somtoday\.nl/home/grades\?-overview(?:[^"]*)"'
        matches = re.findall(pattern, str(rs))
        pages_list = []
        for match in matches:
            m = match.replace('href=', '')
            m = m.replace(r'https://elo.somtoday.nl', '')
            m = m.replace('"', '')
            pages_list.append(m)
        #print(pages_list)
        ak = pages_list[0]
        soup = BeautifulSoup(self.make_request(ak).content, 'html.parser')

        #get gradepage ID list
        gp_id_list = []
        for i in pages_list:
            i = i.replace('/home/grades?-overview=&amp;+detail=', '')
            i = i.replace('&amp;-display=', '')
            gp_id_list.append(i)

        # determine position of specified subject
        subject_pos = available_subjects.index(subject)
        # determine associated ID with subject
        gradepage_id = gp_id_list[subject_pos]
        gradepage_url = f'https://elo.somtoday.nl/home/grades?amp%3B+detail={gradepage_id}&detail={gradepage_id}&amp%3B-display='
        rc = self.make_request(f'/home/grades?amp%3B+detail={gradepage_id}&detail={gradepage_id}&amp%3B-display=').content
        #print(gradepage_url)
        pattern = r'\d+\.\d{2}' # IF the wrong grade is ever returned, here is why:
        matches = re.findall(pattern, str(rc))
        grade = max(matches)
        if len(matches) == 3: 
            return {'grade': grade}
        else:
            return {'grade': -1}

    def get_grades_for_all_subjects(self): # TODO: see get_absences on how this can be optimised
        subjects = self.get_subjects()
        grades = {}
        for subject in enumerate(subjects):
            grades[subject[1]] = self.get_grade_for_subject(subject[1])['grade']
            print(f'info: got {subject[0]+1} grade(s) out of {len(subjects)} total...')
        return grades

    def get_absences(self):
        r = self.make_request('/home/absence')
        soup = BeautifulSoup(r.content, 'html.parser')
        text = str(soup.getText())
        activitylist= []
        durationlist= []
        isafgehandeldlist= []
        datestamplist = []
        for i in text.split('\n'):
            #print(i)
            if i.startswith('A') and not i.startswith('Afwezigheid') and not i.startswith('Afgehandeld') or i.startswith('Zi') or i.startswith('Aan') or i.startswith('Med') or i.startswith('schoola') or i.startswith('Tand'):
                activitylist.append(i)
            elif i.startswith('ma ') or i.startswith('di ') or i.startswith('wo ') or i.startswith('do ') or i.startswith('vr ') or i.startswith('za ') or i.startswith('zo '):
                durationlist.append(i)
            elif i.startswith('Afgehandeld:'):
                i = i.replace('Afgehandeld: ', '')
                isafgehandeldlist.append(i)
            elif re.search(r'\d{2}-', i) or re.search(r'\d{1}e', i) or re.search(r'\d{2}:', i):
                datestamplist.append(i)
        #print(activitylist)
        #print(durationlist)
        #print(isafgehandeldlist)
        #print(datestamplist)
        absence_dict = {}
        for i in enumerate(activitylist):
            i = i[0]
            absence_dict.update({
                i: {
                    'activity': activitylist[i],
                    'duration': durationlist[i],
                    'is_afgehaneld': isafgehandeldlist[i],
                    'datestamp': datestamplist[i],
                }
            })
        return absence_dict

    def get_parent_names(self):
        r = self.make_request('/home/absence')
        soup = BeautifulSoup(r.content, 'html.parser')
        text = str(soup.getText())
        parentlist= []
        for i in text.split('\n'):
            #print(i)
            if i.startswith('Gemeld door: '):
                i = i.replace('Gemeld door: ', '')
                parentlist.append(i)
        
        dedup_parentlist = []
        for i in parentlist:
            if i not in dedup_parentlist:
                dedup_parentlist.append(i)
        
        return dedup_parentlist

    def remove_html(self, x) -> str:
        soup = BeautifulSoup(x, 'html.parser')
        return soup.get_text()

    def get_schedule(self):
        # OFFSETS -> where to look to find additional data for subject (classroom, time, etc)
        off_classroom = +5
        off_time = -6
        off_date =  9

        r = self.make_request('/home/roster')
        soup = BeautifulSoup(r.content, 'html.parser')
        text = str(soup)
        #print(text)
        spagaat = text.split('\n')
        roster_data = {}
        roster_data_id = 0
        for i in enumerate(spagaat):
            line = i[0]
            content = i[1]
            #print(f'info: analyzing line {line}')
            if content.startswith('<h2 class="roosterdetail titel">'):
                plain_c = self.remove_html(content)
                #print(f'info: found subject {plain_c} at line {line}')

                # determine classroom
                classroom = self.remove_html(spagaat[line+off_classroom])
                #print(classroom)

                # determine time
                time = self.remove_html(spagaat[line+off_time])
                #print(time)

                # determine date
                date = self.remove_html(spagaat[line+off_date][7:13])
                date = date.replace(' jan', '-1')
                date = date.replace(' feb', '-2')
                date = date.replace(' mrt', '-3')
                date = date.replace(' apr', '-4')
                date = date.replace(' mar', '-5')
                date = date.replace(' mei', '-5')
                date = date.replace(' jun', '-6')
                date = date.replace(' jul', '-7')
                date = date.replace(' aug', '-8')
                date = date.replace(' sep', '-9')
                date = date.replace(' okt', '-10')
                date = date.replace(' nov', '-11')
                date = date.replace(' dec', '-12')
                current_date_time = datetime.datetime.now()
                date0 = current_date_time.date()
                year = date0.strftime("%Y")
                date += f'-{year}'

                
                roster_data.update({
                    roster_data_id: {
                        'subject': plain_c,
                        'classroom': classroom,
                        'time': time,
                        'date': date
                    }
                })
                roster_data_id += 1
        return roster_data

    def get_homework(self, windowsize=100):
        # OFFSETS -> where to look to find additional data for subject (classroom, time, etc)
        off_description = 1
        off_subject = -7
        off_date = 6

        r = self.make_request(f'/home/homework?windowsize={windowsize}')
        soup = BeautifulSoup(r.content, 'html.parser')
        text = str(soup)
        #print(text)
        spagaat = text.split('\n')
        data = {}
        data_id = 0
        for i in enumerate(spagaat):
            line = i[0]
            content = i[1]
            #print(content)
            #print(f'info: analyzing line {line}')
            if content.startswith('<span class="onderwerp">'):
                #print(f'found homework_event at line {line}')
                header = self.remove_html(content)
                description = self.remove_html(spagaat[line+off_description])

                subject = self.remove_html(spagaat[line+off_subject])
                if subject == '' or subject == ' ' or subject == '   ': # the subject could not be found, which means we are dealing with a test
                    type_ = 'test'
                    #off_subject -= 1 # <span class="icon-toets" title="Toets"></span> takes one extra line 
                    subject = self.remove_html(spagaat[line-8]) # above code doesnt work somehow.
                else:
                    type_ = 'homework'

                #print(f'---\n{header}\n{description}\n{subject}\n{type_}\n---')
                #print(description)
                date = self.remove_html(spagaat[line+off_date])[2:]
                date = date.replace('jan', '-1')
                date = date.replace('feb', '-2')
                date = date.replace('mrt', '-3')
                date = date.replace('apr', '-4')
                date = date.replace('mar', '-5')
                date = date.replace('mei', '-5')
                date = date.replace('jun', '-6')
                date = date.replace('jul', '-7')
                date = date.replace('aug', '-8')
                date = date.replace('sep', '-9')
                date = date.replace('okt', '-10')
                date = date.replace('nov', '-11')
                date = date.replace('dec', '-12')
                date = date.replace('.', '')
                current_date_time = datetime.datetime.now()
                date0 = current_date_time.date()
                year = date0.strftime("%Y")
                date += f'-{year}'
                data.update({
                    data_id: {
                        'subject_acronym': subject,
                        'header': header,
                        'description': description,
                        'type': type_,
                        'date': date
                    }
                })
                data_id += 1
        return data



auth = Auth()
main = Main()
if __name__ == '__main__':
    # Example usage
    print(main.get_absences())
    print(main.get_homework())