  
import os
import re
import json
import pickle
import requests
from bs4 import BeautifulSoup as BS
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from fxp.parser import BASE_DIR, DEFAULT_USER_AGENT, HOST, PREVIEW_URL

class _Base(type):
    # Перехватываем момент создания класса
    def __init__(cls, name, bases, attr_dict):
        super().__init__(name, bases, attr_dict)

    # Перехватываем момент создания объекта
    def __call__(cls, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)
        if cls.__name__ == "Preview":
            cls.__bases__[0].page = obj._Preview__num_page
        return obj

class BaseMeta(metaclass=_Base):
    """Base metaclass"""

class BaseParser(BaseMeta):
    # __metaclass__ = ABC

    def __init__(self, user_agent: str = None):
        self._user_agent = user_agent if user_agent is not None else DEFAULT_USER_AGENT

    def _get_page(self, url):
        if hasattr(self, "page"):
            if self.page < 1:
                raise ValueError("Page is < 1")
        response = requests.get(
            url,
            headers={
                "User-Agent": self._user_agent
            }
        )
        # if hasattr(self, "page"):
        #     if not response.url.endswith(str(self.page)) and self.page != 1:
        #         raise ValueError("Page is very big!")
        if response.status_code == 200:
            return BS(response.text, features="html.parser")
        raise ValueError("Response not 200")

    @abstractmethod
    def save_to_file(self, name: str) -> None:
        """Save news to file
        Args:
            name (str): [description]
        """

    @abstractmethod
    def save_to_json(self, path: str) -> None:
        """Save news to json file
        Args:
            path (str): [description]
        """


class Preview(BaseParser):
    def __init__(self, **kwargs):
        super().__init__(kwargs.get("user_agent"))
        self.__num_page = kwargs.get("page") if kwargs.get("page") is not None else 1
        self.__links = []

    def get_links(self):
        try:
            html = self._get_page(PREVIEW_URL.format(HOST, self.__num_page))
        except ValueError as error:
            print(error)
            # self.__links = []
        else:
            box = html.find("div", attrs={"class": "largeTitle"})
            if box is not None:
                articles = box.find_all(
                    "article", attrs={"class": "js-article-item articleItem"})
                for article in articles:
                    link = article.find("a", attrs={"class": "title"})
                    self.__links.append(HOST + link.get("href"))
            else:
                self.__links = []

    def __iter__(self):
        self.__cursor = 0
        return self

    def __next__(self):
        if self.__cursor == len(self.__links):
            raise StopIteration
        try:
            return self.__links[self.__cursor]
        finally:
            self.__cursor += 1

    # Реализовать метод, который будет возвращать новый объект, содержащий срез из элементов списка
    def __getitem__(self, index):
        try:
            # if type(index) == int:
            if isinstance(index, int):
                res = self.__links[index]
                return res
            # elif type(index) == slice:  
            elif isinstance(index, slice):    
                obj = Preview()
                obj._Preview__links = self.__links[index]
                return obj
            else:
                raise TypeError
        except TypeError:
            print("Ошибка TypeError. Ожидается int или slice")
        except IndexError:
            print("Выход за границы списка")

    def save_to_file(self, name):
        path = os.path.join(BASE_DIR, name + ".bin")
        pickle.dump(self.__links, open(path, "wb"))


    def save_to_json(self, name):
        path = os.path.join(BASE_DIR, name + ".json")
        json.dump(self.__links, open(path, "w"))


class NewsParser(BaseParser):
    def __init__(self, user_agent: str = None):
        super().__init__(user_agent)
        self.date_pattern = re.compile(r"[A-Za-z]{3} \d{2}, \d{4} \d{2}:\d{2}[A-Za-z]{2}")
        self.news = {}

    def __call__(self, url):
        try:
            html = self._get_page(url)
        except ValueError as error:
            print(error)
        else:
            box = html.find("section", attrs={"id": "leftColumn"})
            if box is not None:
                self.news["head"] = box.find("h1", attrs={"class": "articleHeader"}).text
                box_date = box.find("div", attrs={"class": "contentSectionDetails"})
                date = box_date.find("span").text
                date = re.search(self.date_pattern, box_date.find("span").text)
                self.news["date"] = (
                    datetime.strptime(date.group(0), "%b %d, %Y %H:%M%p").replace(tzinfo=timezone.utc).timestamp()
                )
                article = box.find("div", attrs={"class": "articlePage"})
                self.news["img_src"] = article.find("img").attrs["src"]
                text_blocks = article.find_all("p")
                self.news["text"] = "\n".join([p.text for p in text_blocks]).strip()
        self.save_to_json(
            datetime.fromtimestamp(self.news["date"]).strftime("%Y/%m/%d/%H_%M")
        )
                

    def save_to_json(self, name):
        path = os.path.join(BASE_DIR, name + ".json")
        dirs = os.path.split(path)[:-1]
        try:
            os.makedirs(os.path.join(*dirs))
        except Exception as error:
            print(error)
        json.dump(self.news, open(path, "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":  
    
    # for page in range(1, 11):
    #     links = Preview(page=page)
    #     links.get_links()
    #     news = NewsParser()
    #     # news.__call__(links[0])
    #     pool = ThreadPoolExecutor()
    #     start = datetime.now()
    #     news_from_page = pool.map(news, links)
    #     for n in news_from_page:
    #         pass
    #         # print(n)
    #         # print("=" * 150)
    #     print(datetime.now() - start)
    

    # start = datetime.now()
    # pool = ThreadPoolExecutor(max_workers=14)
    # news_from_page = pool.map(news, links)
    # for n in news_from_page:
    #     print(n.result)
    # print(datetime.now() - start)
    

    # start = datetime.now()
    # for url in links:
    #     print(news(url))
    # print(datetime.now() - start)
    


    # # for i in links._Preview__links:
    # #     print(i)
    # links.save_to_json('tmp_links_2')
    # links.save_to_file('tmp_links_2')
    # for link in links:
    #     print(link)
    # print(len(links._Preview__links))
    
    links = Preview(page=1)
    links.get_links()
    for link in links._Preview__links:
        print(link)
    print(links._Preview__links.__len__())
    print("=" * 200)
    # news(links[0])
    # print(links[-13], end="\n\n")
    # print([el for el in links[1:2]], end="\n\n")
    # print([el for el in links[:2:1]], end="\n\n")
    # print([el for el in links[:-5:1]], end="\n\n")
    # print(links["key"]) # Как обратиться к элементу списку по ключу?