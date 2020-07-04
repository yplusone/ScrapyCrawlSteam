# -*- coding: UTF-8 -*-
import html
import json
import scrapy
from ..items import SteamItem
import re
from bs4 import BeautifulSoup


class ItcastSpider(scrapy.Spider):
    name = 'game'
    allowed_domains = ['store.steampowered.com']

    # 生成列表页url
    start_urls = []
    base_url = 'https://store.steampowered.com/search/?category1=998&page={}'
    for page in range(1, 3):
        start_urls.append(base_url.format(page))
        # break

    def parse(self, response):
        a_list = response.xpath('//*[@id="search_resultsRows"]/a')
        print(len(a_list))
        for a in a_list:
            item = SteamItem()
            # 统一设置默认值
            item["game_name"] = ''
            item["detail_url"] = ''
            item["release_date"] = ''
            item["publisher"] = ''
            item["developer"] = ''
            item["tags"] = ''
            item["game_price"] = ''
            item["game_review"] = ''
            item["info"] = ''
            item["imgs"] = ''
            item["review_list"] = ''

            detail_link = a.xpath('./@href').extract()[0]
            try:
                item["detail_url"]=detail_link
                game_name = a.xpath('./div[2]/div/span/text()').extract()[0]
                release_date = a.xpath('./div[2]/div[2]/text()').extract()[0]
                game_price = a.xpath('./div[2]/div[4]/div[2]/text()').extract()[0].strip() #　如果是正常价格
                if not game_price:      #　看看是否是打折价格
                    game_price = a.xpath('./div[2]/div[4]/div[2]/span/strike/text()').extract()[0].strip()
                    price_discount = a.xpath('./div[2]/div[4]/div[1]/span/text()').extract()[0].strip()    #　如果有打折，提取折扣力度
                else:
                    price_discount = '-0%'
                print(game_name)
                item["game_name"] = game_name
                item["release_date"] = release_date
                item["game_price"] = game_price
                item["price_discount"] = price_discount
            except Exception as e:
                print('名字／发布时间／价格／折扣　缺失')
                print(e)
                print('detail_link', detail_link)
                continue

            # 请求详情页
            detail_request = scrapy.Request(

                url=detail_link,
                callback=self.detail_parse,
                headers={
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
                },
                meta={"item": item, 'detail_link': detail_link},
            )
            yield detail_request



    def detail_parse(self, response):
        item = response.meta["item"]
        detail_link = response.meta["detail_link"]
        try:
            game_summary = response.xpath('//div[@class="game_description_snippet"]/text()').extract()[0].strip()
            game_review = response.xpath('//div[@class="user_reviews"]/div[2]/@data-tooltip-html').extract()[0]
            game_img = response.xpath('//img[@class="game_header_image_full"]/@src').extract()[0]
            publisher = response.xpath('//div[@class="dev_row"]/div[@class="summary column"]/a/text()').extract()[0]
            developer = response.xpath('//div[@class="dev_row"][1]/div[@class="summary column"]/a/text()').extract()[0]
            sels_list = response.xpath('//div[@class="glance_tags popular_tags"]/a')
            tags=''
            print(len(sels_list))
            for sel in sels_list:
                text = sel.xpath('.//text()').extract()[0].strip()
                tags+=text
                tags+=" "

            print(tags)
            item["publisher"] = publisher
            item["developer"] = developer
            item["tags"] = tags
            item["game_review"] = game_review
            item["info"] = game_summary
            item["imgs"] = game_img
        except Exception as e:
            print('简介／评论／图片　缺失')
            print(e)

        # 生成评论页url
        try:
            game_id = re.search('https://store.steampowered.com/app/(\d+)/.*?', detail_link).group(1)
            review_url = "https://store.steampowered.com/appreviews/{}?filter=summary&language=schinese&l=schinese".format(game_id)

            # 请求评论页
            review_request = scrapy.Request(
                url=review_url,
                callback=self.review_parse,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
                },
                meta={"item": item},
            )

        except Exception as e:
            print('正则', detail_link)
            print(e)
            review_request = ''

        yield review_request

    def review_parse(self, response):
        item = response.meta["item"]
        review_list = []
        try:
            # 获取json数据中的html文本
            data = response.text
            data_dict = json.loads(data)
            data_html = html.unescape(data_dict["html"])

            # 　构建bs4对象
            soup = BeautifulSoup(data_html, 'lxml')
            div_list = soup.select('div[class="content"]')
            for div in div_list:
                review = div.get_text()
                rev = review.strip()
                if rev:
                    review_list.append(rev)
        except Exception as e:
            print('评论缺失，无法解析')
            print(e)

        item["review_list"] = review_list
        yield item
