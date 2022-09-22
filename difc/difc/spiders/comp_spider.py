import scrapy
from scrapy.http import HtmlResponse
import pymongo
import time
import csv
import os


class comp_spider(scrapy.Spider):
    """_summary_

    This is the spider we will use to scrap data from 'https://www.difc.ae'.
    The spider will open the main page and request pages from each url while it's valid.
    For each new page, the spider will scrape every company available on that page.
    the results will be yielded and saved directly to MongoDP. 
    """

    # the Global variables which we will need across the functions bok
    name = "comp_spider"
    comp_scraped = 0
    current_page = 0
    end = {}
    params = ['url']
    headers = {'Origin': 'https://www.difc.ae'}
    info = []
    comps_and_individuals = {}

    # then we make the connections to MongoDB
    # In this example we will connect using the account admin:admin
    client = pymongo.MongoClient(
        "mongodb+srv://admin:admin@companies.caxacha.mongodb.net/?retryWrites=true&w=majority")
    # Companies_DataBase.scrapped_companies is the collection which has data about the companies
    db = client.Companies_DataBase.scrapped_companies
    # Companies_DataBase.comps_and_individuals is the collections which has the associations between Directors of companies and companies
    association = client.Companies_DataBase.comps_and_individuals

    def start_requests(self):
        """_summary_

        The first function which will be called.
        This function will request new pages to be scrape while,
        the number of pages needed hasn't been reached yet.

        For each page, a new request will be made for each
        company on that page, to scrape its data.
        """
        # to collect at least a thousand page, we will scrape companies from tow categories: Regulated & Non Regulated
        urls = [
            "https://retailportal.difc.ae/api/v3/public-register/overviewList?page={page}&keywords=&companyName=&registrationNumber=&type=Non%2520Regulated&status=&latitude=0&longitude=0&sortBy=&difc_website=1&data_return=true&isAjax=true",
            "https://retailportal.difc.ae/api/v3/public-register/overviewList?page={page}&keywords=&companyName=&registrationNumber=&type=Regulated&status=&latitude=0&longitude=0&sortBy=&difc_website=1&data_return=true&isAjax=true"
        ]
        start_time = time.time()
        for i, url in enumerate(urls):
            # For each URL we will scrape all the available pages.
            # We will stop when the number of scraped pages is satisfied
            # or until we we exhausted all the pages of the given url
            self.current_page = 0
            self.end[i] = False
            while self.comp_scraped < 1000 and self.end[i] == False:
                self.current_page += 1
                try:
                    yield scrapy.Request(url=url.format(page=self.current_page), callback=self.parse_for_comps, headers=self.headers, meta={"end": i})
                except:
                    print("Invalid URL!")

        # After scrapping all the data We need to upload it to Mongo DP
        total_scrapping_time = time.time() - start_time
        print("scrapped ", self.comp_scraped, " websites!")
        print("Total time : ", total_scrapping_time, "seconds")
        # (optional) Delete the current data on Mongo DP
        self.db.delete_many({})
        self.association.delete_many({})
        self.db.insert_many(self.info)
        # To upload the associations in a clear way,
        # we will transform the dictionary of arrays to an
        # array of dictionaries.
        up = []
        for key, val in self.comps_and_individuals.items():
            if len(val) == 1:
                up.append({key: val[0]})
            else:
                up.append({key: val})

        self.association.insert_many(up)
        os._exit(0)

    def parse_for_comps(self, response):
        """_summary_
        This function receive a full page to be sracped.
        Each page have several companies to be sracped further.

        The response collected will in form of a serialized a dictionary
        If the response is valid(the page we requested exist), the data will be in response['data']
        """

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

    def get_comp_dat(self, response):
        """_summary_
        This is function collects the data from the company page,
        It stores all the data in the self.info directly.
        """
        print("scrapping:", response.url)
        original_url = response.url
        self.comp_scraped += 1

        # To collect the all the data of the companies we will use two Xpath selectors,
        # as all the needed information exist only in tow unique HTML tags.
        Q1 = "//div[@class='row']/div[@class='col-sm-6 col']/p/strong/text()"
        Q2 = "//div[@class='row']/div[@class='col-sm-6 col']/p/text()"
        all_data = response.xpath(Q1 + "|" + Q2).getall()

        #We applying cleaning algorithm to extract the fields and values
        #for the given company 
        comp_keys, comp_values = self.clean(all_data)

        #now that we have the fields and values we iterate on them adding
        #them to self.info
        comp_data = {}
        comp_data["url"] = original_url
        for key, val in zip(comp_keys, comp_values):
            comp_data[key] = val
            if key not in self.params:
                self.params.append(key)

        #And finally we also add the associations between individuals and companies
        if "Directors" in comp_data.keys():
            self.make_assos(comp_data["Directors"], comp_data["Name"])
        self.info.append(comp_data)

    def clean(self, all_data):
        """_summary_
        Clean function is responsible of cleaning the data we get from the xpath queries,
        it return two lists which holds all the data of a company in the form of its fields and values.
        """
        keys = []
        values = []

        pointer1 = 0
        pointer2 = 0

        #We will use a two pointers algorithm to to extract all the needed data
        all_data = [val for val in all_data if "\n" not in val or val == ""]
        while pointer1 < len(all_data):
            while pointer1 < len(all_data) and ":" not in all_data[pointer1]:
                pointer1 += 1
            if pointer1 >= len(all_data):
                break
            keys.append(all_data[pointer1][:all_data[pointer1].find(":")])
            pointer1 += 1
            pointer2 = pointer1
            vv = []
            while pointer2 < len(all_data) and ":" not in all_data[pointer2]:
                vv.append(all_data[pointer2])
                pointer2 += 1
            if len(vv) == 1:
                values.append(vv[0])
            elif len(vv) == 0:
                values.append(None)
            else:
                values.append(vv)

        return keys, values

    def make_assos(self, names, comp):
        """_summary_
        this function will create the associations we need between individuals and the companies.
        Args:
            names stf/list: _description_
            comp str: _description_
        """
        if isinstance(names, str):
            if names not in self.comps_and_individuals.keys():
                self.comps_and_individuals[names] = []
            if comp not in self.comps_and_individuals[names]:
                self.comps_and_individuals[names].append(comp)
        else:
            for name in names:
                if name not in self.comps_and_individuals.keys():
                    self.comps_and_individuals[name] = []
                if comp not in self.comps_and_individuals[name]:
                    self.comps_and_individuals[name].append(comp)


# scrapy crawl comp_spider -L WARNING
