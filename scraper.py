#Author: Peter Swanson
#Created for Ag for Hire

import mechanize    #Mechanize for accessing forms and controls
from BeautifulSoup import BeautifulSoup #BS for parsing HTML
import cookielib    #CookieLib for storing cookies
import string   #String to remove certain escape sequences
import re   #re for regex to find emails in text
import pandas as pd #Pandas to make into dataframe and write to excel
import json #For serialization

jobs = {}  #Dict to hold all
json_jobs = {} #Dict to hold serialized data

class Job(object): #Class object to hold all relevant info
    def __init__(self):
        self.title = ""
        self.company = ""
        self.location = ""
        self.posted_date = ""
        self.description = ""
        self.additional_info = ""
        self.contact = ""
        self.calJobsURL = ""
        self.keyword = ""

def login(link): #To login to CalJOBS

    browser = mechanize.Browser() #Create virtual browser
    cj = cookielib.LWPCookieJar() #create object to store cookies
    browser.set_cookiejar(cj) #connect browser to cookies
    browser.set_handle_equiv(True)
    browser.set_handle_redirect(True) #Handlers and Headers to trick the site into not thinking this is a bot
    browser.set_handle_referer(True)
    browser.set_handle_robots(False)
    browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:21.0) Gecko/20100101 Firefox/21.0'),
                              ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                              ('Accept-Language', 'en-gb,en;q=0.5'),
                              ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),('Connection', 'keep-alive')]

    browser.open(link) #Open the link to the login page
    browser.select_form(name="aspnetForm") #Select the login form

    for control in browser.form.controls:
        if control.type == "text":
            control.value = 'topazoo42'
        elif control.type == "password":    #Enter login information
            control.value = '1121Error!'

    browser.submit() #Submit the form

    if "START_PAGE" in browser.geturl(): #Check for successful login
        print "Successfully logged in!"

    return browser

def open_job_search(page, URL): #open the job search page in the browser
    page.open(URL)
    if "session=jobsearch" in page.geturl(): #check if job search page opened
        print "Successfully opened job search page!"

    return page

def get_table_info(html): #Get links from job listings
    parsed = BeautifulSoup(html) #parse the page
    page_links = []

    for link in parsed.findAll("a", { "class" : "visitedlink" }):
        if "assessment" not in link['href']: #Get all links to jobs in the table and return them
            page_links.append(link['href'])

    return page_links

def make_pretty(text): #Take blocks of text, clean them up and make them ascii
    printable = set(string.printable) #Set of all printable characters
    text = filter(lambda x: x in printable, text) #used to remove non-printable characters
    text = str(text) #make sure its a string

    if "Partial Job Description&nbsp;" in text:
        text = text.replace("Partial Job Description&nbsp;", "")

    elif "Job Description&nbsp;" in text:
        text = text.replace("Job Description&nbsp;", "")

    if "&bull;" in text:
        text = text.replace("&bull;", '-')

    if "&ndash;" in text:
        text = text.replace("&ndash;", '-')

    if "&rsquo;" in text:
        text = text.replace("&rsquo;", '\'')

    if "&rdquo;" in text:
        text = text.replace("&rdquo;", '\"')    #Remove Unicode

    if "&ldquo;" in text:
        text = text.replace("&ldquo;", '\"')

    if "&nbsp" in text:
        text = text.replace("&nbsp;", ": ")

    if "&hellip" in text:
        text = text.replace("&hellip", "...")

    if "&nbspSave" in text:
        text = text.replace("&nbspSave;", "Save")

    if "&mdash;" in text:
        text = text.replace("&mdash;", "-")

    return text

def visit_collector(links, browser, keyword): #Take all links and visit their page
    print "Collected", len(links), "jobs."

    for link in links: #for each link
        new_job = Job() #create a new job object
        browser.open(link) #open the current link
        page = BeautifulSoup(browser.response().read()) #read the page

        try:
            new_job.calJobsURL = browser.geturl() #store the URL
            new_job.title = page.find("span", { "class" : "jobSummaryTitle" }).text #Store the title
            new_job.company = page.find("span", { "class" : "jobSummaryCompany" }).text #Store the company
            new_job.location = page.find("span", {"id": "ctl00_Main_content_JobLocationLabel"}).text #store the location
            new_job.posted_date = page.find("span", {"id": "ctl00_Main_content_JobPostedDateLabel"}).text #store the date
            new_job.keyword = keyword #store the keyword
        except AttributeError:
            continue

        legends = page.findAll("fieldset")
        for legend in legends:
            if "Job Description" in legend.text:
                text = make_pretty(legend.text)
                if len(text) < 1:
                    new_job.description = "None"    #Get and clean the job description if it exists
                else:
                    new_job.description = text

                email = re.search(r'[\w\.-]+@[\w\.-]+', text) #if email in text, get it

                try:
                    new_job.contact = email.group(0)
                except AttributeError:
                    new_job.contact = "No contact information."

            if "Additional Information" in legend.text: #Get and clean the additional information if it exist
                text = make_pretty(legend.text)
                text = text.replace("Additional Information:", "")
                text = text.replace("Additional Information", "")

                if len(text) < 1:
                    new_job.additional_info = "None"
                else:
                    new_job.additional_info = text

                if new_job.contact == "No contact information.":

                    email = re.search(r'[\w\.-]+@[\w\.-]+', text) #i email in text, get it

                    try:
                        new_job.contact = email.group(0)
                    except AttributeError:
                        new_job.contact = "No contact information."

        jobs[new_job.calJobsURL] = new_job #Store job in dictionary by URL to ensure no duplicates!

        browser.back()

def search_by_keyword(keyword, job_search_page): #search the job page with a keyword
    job_search_page.select_form(name="frmQuickSearch") #select the quick search form
    control = job_search_page.form.find_control("keyword") #find the place to insert a keyword
    control.value = keyword #insert keyword

    print "Entered search term:", keyword

    job_search_page.submit(nr=0) #submit form

    try:
        job_search_page.select_form(name="frmJoblist")
        control = job_search_page.form.find_control("rows") #Record 500 results, can be changed!
        control.value = ["10"] #Change number of jobs grabbed
        job_search_page.submit(name="cmdSubmit")

    except:
        pass


    return job_search_page

def search_calJobs(keywords): #main loop for searching and visiting links
    main_page = login('https://www.caljobs.ca.gov/vosnet/loginintro.aspx?login=e')

    for keyword in keywords:
        job_search_page = open_job_search(main_page, "https://www.caljobs.ca.gov/jobbanks/default.asp?p=0&session=jobsearch&geo=0601000000")
        results = search_by_keyword(keyword, job_search_page)
        job_listings = get_table_info(results.response().read())
        visit_collector(job_listings, job_search_page, keyword)


def make_spreadsheet(): #Record data
    titles = []
    companies = []
    locations = []
    posted_dates = []
    descriptions = []
    additionals = []
    contacts = []
    calJobsURLs = []
    keywords = []

    for job in jobs.values():
        titles.append(job.title)
        companies.append(job.company)
        locations.append(job.location)  # Store all these in lists
        posted_dates.append(job.posted_date)
        descriptions.append(job.description)
        additionals.append(job.additional_info)
        contacts.append(job.contact)
        calJobsURLs.append(job.calJobsURL)
        keywords.append(job.keyword)

    overview = zip(titles, companies, locations, posted_dates, descriptions, additionals, contacts, calJobsURLs, keywords) #Zip
    frame = pd.DataFrame(list(overview), columns = ['Title', 'Company', 'Location', 'Posted Date', 'Description', 'Additional Info', 'Contact Info', 'CalJobs URL', 'Keyword'])
    #^^^Create a dataframe and format for spreadsheet

    with pd.ExcelWriter('Scraper_Demo.xlsx') as writer:
        frame.to_excel(writer, 'Jobs') #Write
        writer.save()

def write_json():
    for job in jobs.values():
        with open("json.txt", "a") as outfile:
            json.dump({'Keyword': job.keyword, 'URL': job.calJobsURL, 'Contact': job.contact,
                       'Additional_info': job.additional_info, 'Description': job.description, 'Date': job.posted_date,
                       'Location': job.location, 'Company': job.company, 'Title': job.title}, outfile, indent=4, sort_keys=True)
            outfile.write('\n')

        #json_jobs[job.calJobsURL] = job_json

def main():

    try:
        search_calJobs(["harvest"]) #search with keyword

    except mechanize.URLError:
        print "Connection was terminated by CalJobs, saving collected data..."

    #make_spreadsheet()
    write_json()

main()