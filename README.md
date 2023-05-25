# Pagerduty-importer #

### What is this repository for? ###

* This app is an script to import the pagerduty incients, parse to a csv file and finally send by email address
* You can select import all incidents inside the date range, on call hours, or working hours incidents

### How does it work? ###

* You need a pagerduty-importer.env tih the PAGERDUT_TOKEN, and if you want the SPARKPOST_API_KEY to send with email.
* You can use the srcript with python importer.py --start_date 2023-03-01 --end_date 2023-03-30 -all_hours --filename import --email random@gmail.com
