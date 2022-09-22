# Schwarzthal-Tech Entry-Task

Task submission for Entry task to Schwarzthal-Tech as a Data Engineer, 

_Kamil Sabbagh, September 2021_

---

## Table of contents
1. [ Introduction ](#intro)
2. [ Scrapy ](#Scrapy)
3. [ MongoDP ](#MongoDB)
4. [ Implementing the code ](#Implemention)
5. [ Conclusion ](#Conclusion)
___
<a name="intro"></a>
## 1. Introduction
In this project, we implemented a Spider using Scrapy framework to scrape data about companies from the website [difc](https://www.difc.ae). Furthermore, a table of associations has been made to connect Directors of companies with which companies they are associated. And finally, the data has been loaded to MongoDB database in two separate collections, one for the information about the company, and one for the associations between directors and companies.

<a name="Scrapy"></a>
## 2. Scrapy
The majority of the code was done on `Spiders/comp_spider`.

In this specific task, we choose not to utilize the `items.py` provided by scrapy framework. As the fields for each company were not consistent over all the companies. Furthermore, to create the association table the data of all the companies needed to be collected first before parsing it.

  - ### Getting the pages
    - To scrape the data we made the observation that the website is using infinite scrolling, so while scrolling the website will make ajax calls to get the data of the next pages.
    - Therefore, the implementation makes use of this observation, so we call each available page in two categories. companies that are labeled `Regulated` and companies that are labeled `Non Regulated`
    ```
    for i, url in enumerate(urls):
            # For each URL we will scrape all the available pages.
            # We will stop when the number of scraped pages is satisfied
            # or until we we exhausted all the pages of the given url
            self.current_page = 0
            self.end[i] = False
            while self.comp_scraped < 1000 and self.end[i] == False:
                self.current_page += 1
                try:
                    yield scrapy.Request(url=url.format(page=self.current_page), callback=self.parse_by_page, headers=self.headers, meta={"end": i})
                except:
                    print("Invalid URL!")
    ```
    - Each time we make a new request we will call the function `parse_by_page`.
  
    - `parse_by_page` will receive the data of the page in the form of a `JSON` file which can't be directly used. The HTML which is useful for and can scrap is located in the `data` field of this JSON file so we extract it.
    
    ```
    text = response.text.replace('true', 'True')
        text = text.replace('false', 'False')
        # So we deserialize the dictionary
        temp_data = eval(text)
        if 'data' in temp_data:
            data = temp_data['data']
            # we create the new response using the HTML in 'data'
            new_response = HtmlResponse(
                url="my HTML string", body=data, encoding='utf-8')

            # We use Xpath to collect all the links of the available companies
            # and make a new request to scrap the data from there.
            links = list(dict.fromkeys(new_response.selector.xpath(
                '//a[contains(@href, "w")]/@href').getall()))
            for i, link in enumerate(links):
                links[i] = "http://" + \
                    link[link.find("www"):link.find(
                        '<')].replace("\\", "") + "/"
                yield scrapy.Request(url=links[i], callback=self.get_comp_dat)
        else:
            self.end[response.meta.get('end')] = True
    ```
    - Now for every call of `parse_by_comp`, We will give it the url of one company.
    - here we make the observation that all the needed fields and values are in unique `HTML` tags:
    ```
    <div class='class="col-sm-6 col'>
        <p>
            <strong> filed name </strong>
        </p>
    </div>
    <div class='class="col-sm-6 col'>
        <p>
            Value of the field
        </p>
    </div>
    ```
    - So by requesting all the data in these two tags we can get all the field names and values for a given company.
    - We process all the data and add it to `self.info` and `self.comps_and_individuals`

<a name="MongoDB"></a>
## 3. MongoDB
We used MongoDB a NOSQL data to store our data. The data will be stored in the data base `Companies_DataBase` in two collections `scrapped_companies` and `comps_and_indiv`.

First things first we should add the connection string to mongoDB to `.env variable` located in `/difc/.env`.
In there you should edit the file adding your connection string:
```
MongoDB_connection_string = {adding your MongoDB string connection here}
```
The crawler will create the databases and collections needed automatically.

The Data collected in `scrapped_companies` will hold all the available information for a given company:
```
{"_id":{"$oid":"632c267575f694dbac144a73"},"url":"https://www.difc.ae/public-register/dp-bioinnovations-ltd/","Status of registration":"Active","Business activities":"Technology Research & Development","Registered Number":" 6127","Registered offices":" Unit GA-00-SZ-L1-RT-201, Level 1, Gate Avenue - South Zone, Dubai International Financial Centre, Dubai, , United Arab Emirates","Name":"D&P Bioinnovations Ltd","Trading Name":"D&P Bioinnovations Ltd","Status of Registration":"Active","Type of License":"Non Regulated","Legal Structure":"Private Company"," Date of Incorporation ":"20 09 2022","Commercial License Validity Date":"19 09 2023","Directors":"Derek Dashti","Shareholders":"Derek Dashti","Company Secretary":"Derek Dashti","DNFBP":"Not Applicable","Financial Year End":null,"Share Capital":null,"Data Protection Officer Appointed":"No","Notifications":null,"Personal Data Processing Operations":"No","Transfer of Personal Data from the DIFC":"No","Processing of Special Categories of Personal Data":"No"}
```

The data collected in `comps_and_indiv` will hold all associations between Directors and companies:
```
{"_id":{"$oid":"632c267775f694dbac144ec3"},"Derek Dashti":"D&P Bioinnovations Ltd"}

{"_id":{"$oid":"632c267775f694dbac144ee1"},"Jake El Mir":["Simly Technology Ltd","Blink Technology Ltd"]}
```
<a name="Implemention"></a>
## 4. Implementing the code
First, we should make sure that we are in the correct path `/Schwarzthal-Tech-Entry-Task`. Then we need to install the requirements from `requirements.txt` using the command line:
```
pip install -r requirements.txt
```
Next make sure you added the connection string to mongoDB to `.env variable` located in `/difc/.env`.
In there you should edit the file adding your connection string:
```
MongoDB_connection_string = {adding your MongoDB string connection here}
```
Now we have all the needed requirements we can simply run the crawler using the command line:
make sure sure you are in `/difc/`:
```
scrapy crawl comp_spider
```
<a name="Conclusion"></a>
## 5. Conclusion
In this task, we successfully implemented a company scraper. We worked with Scrapy framework and mongodb. We used scrapy to scrape and parse over 1000+ companies and scrape the needed information, and finlay store on MongoDB.

