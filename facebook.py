import json
import httpx
import urllib.parse
from bs4 import BeautifulSoup
from capmonster_python import RecaptchaV2Task
import time
import uuid
import re
from fake_useragent import UserAgent

class Facebook:
    def __init__(self, capmonster_api_key: str = None, proxy: str = None):
        self._proxy = proxy
        self.cookies = None
        self._fb_dtsg = None
        self._ad_act_id = None
        self.capmonster_api_key = capmonster_api_key
        self._client = httpx.Client(
            proxies=f"http://{self._proxy}" if self._proxy else None,
            timeout=httpx.Timeout(5.0, read=30.0),
            transport=httpx.HTTPTransport(retries=3),
            follow_redirects=True
        )
        ua = UserAgent()
        self._client.headers.update({
            "User-Agent": ua.chrome
        })

    def _refresh_fb_dtsg(self):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        r = self._client.get("https://web.facebook.com/&", headers=headers)
        if "checkpoint" in str(r.url):
            raise Exception("CHECKPOINT")
        try:
            self._fb_dtsg = re.search(r'"DTSGInitialData":{"token":"(.*?)"', r.text).group(1)
        except:
            raise Exception("LOGIN_FAILED")

    def _refresh_ad_act_id(self):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        r = self._client.get("https://adsmanager.facebook.com/adsmanager/manage/accounts", headers=headers)
        self._ad_act_id = re.search(r"act=(\d+)", r.text).group(1)

    def login(self, username: str = None, password: str = None, cookies: str = None):
        if username and password:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1"
            }
            r = self._client.get("https://web.facebook.com/", headers=headers)
            privacy_mutation_token = re.search(r'privacy_mutation_token=(.*?)"', r.text).group(1)
            self._client.cookies.update({"datr": re.search(r'"_js_datr","(.*?)"', r.text).group(1)})
            soup = BeautifulSoup(r.text, "html.parser")
            lsd = soup.find("input", {"name": "lsd"}).get("value")
            jazoest = soup.find("input", {"name": "jazoest"}).get("value")

            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://web.facebook.com/",
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
            }
            body = urllib.parse.urlencode({
                "jazoest": jazoest,
                "lsd": lsd,
                "email": username,
                "login_source": "comet_headerless_login",
                "next": "",
                "encpass": f"#PWD_BROWSER:0:{round(time.time())}:{password}",
            })
            r = self._client.post(f"https://web.facebook.com/login/?privacy_mutation_token={privacy_mutation_token}", headers=headers, data=body, follow_redirects=False)
            if "c_user" not in dict(r.cookies) or "xs" not in dict(r.cookies):
                raise Exception("LOGIN_FAILED")

            self.cookies = dict(self._client.cookies)
        if cookies:
            if ";" in cookies:
                cookies = {c.split("=")[0].strip(): c.split("=")[1].strip() for c in cookies.split(";")}
            else:
                cookies = json.loads(cookies)
                if type(cookies) == list:
                    cookies = {c["name"]: c["value"] for c in cookies}
            self.cookies = cookies
            self._client.cookies.update(self.cookies)

        self._refresh_fb_dtsg()

    def like(self):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://web.facebook.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        variables = json.dumps({
            "input":{
                "attribution_id_v2":"CometHomeRoot.react,comet.home,via_cold_start,1698005027853,771399,4748854339,",
                "feedback_id":"ZmVlZGJhY2s6MjM2MTgyNDc4NzMzNjI2Ng==",
                "feedback_reaction_id":"1635855486666999",
                "feedback_source":"NEWS_FEED",
                "is_tracking_encrypted":True,
                "tracking":["AZVICwQDu_6CuVjivB0boF7oh9qyGyWQwJiVJrEJFBirvK95EFA9MNT24LkOORLrm1OJTGj1omKZwxWzV9QdyPtsZVyp-Vjko4NtjsCS-9eHO8JzG-l3Fm9dt6LlrnEhq_yIf2Mj10TrvVsDMyw3XKnTVv_PlNEWSaSxpJfUHVqFnflx6oizrDVSgbdMmqCL2pJY4EIcSCYDLfJ1-KP_zbmSym3_pW4QXs5CxzrmHAlbOr7K7nvIokq_kbXPJiikxp4XTduon0LVR66jy58ZgTfw5C6P6M_5198nnz7Z4SoTZGZ3qmMk40LBgeck8-XLajwGu-IwumEe_lEceHx8WcVQLqBH3UFmIwMgXUUZrdcUCsLsmy-2IrUh-6e8gYp97ou-uimtQf-ACNTeJjvCkgPUi_mgnWMuVT2EdOXdkRhL2skvxf1Q6nnhXyQdTd3BJDXzNFtG4MDphfR0AoRueDV2-mN4i4ODFJFJS9qi-KBP31gpDrW2pU7OB7Dun4ypIlZbbAOx_Y7sq7Tbggxhf692go_gax17xAfKv-8LvY5SB3ze1q0p1fD95hGjR2exnDoNsDpesMDLaH5kpwGoJ1TINavjynJWkweQWIBMxyupDASTbcpQlTpPb6zxJOovYfy068ArniXnfH6c1m_TO4YQX83xY-2UopZwnqnbmeZr4SrplcYkODrvOzEY9Z5ax1apfQpIkFd6xAFGYbCCvLzamPVNhJmnYs0WiDgouKRxu6Abut2QN1XMW94654MsBxpwiNDCS8ey63WWdZgBHh7hddJy14wqNKmwgdBL2D12pku-gAU69CiezCQSPNTEiiLpxNDyMgDyw21gKyaKa8Ikwshk_LNhi_1tG71gNrVz8MAFzerV6jUAfgI4zYu_hVmCHIbmcrQtHNcdsu8cXOTK___zyKMJonbqSsDBIwA0gYuGqrXYpJqekqxH6xPdv4F1dKF4nPb-waiSm4u6d0h-MY5JqI9tVy35J-gQQiNjUZmfzyDbla8fIGr4sJzMHErkldc9kbVSdEo_ZposU7ys7aMCRAKKzc0fKqOFCd0g4P6S5pIw-sRuVOvkbPjHQx_IrnpwBOj93CngmzfeKkBJnSnjsaUhmX0oymbo78vgPnfsuf2CidniWePuCXFEeAHy2H2GilDPDBPjR35KWnYbAJ-ChlXaFgG2vEJK7HA4VTczD5Y1V_FQCZoSUKuV0uqexnodNKnMS0fWSpO5Y-vnVlBQxRhfrCozmh-T0XlAjA"],
                "session_id":"38cb90fb-e05d-4cba-9b80-08d2d1d9c0f2",
                "actor_id":self.cookies.get("c_user"),
                "client_mutation_id":"2"},
            "useDefaultActor":False,
            "scale":1
        })
        body = {
            "variables": variables,
            "doc_id": "6623712531077310",
            "fb_dtsg": self._fb_dtsg
        }
        # body = f"variables={urllib.parse.quote(variables)}&doc_id=7250495224992687&fb_dtsg={urllib.parse.quote(self._fb_dtsg)}"
        r = self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)


    def call(self, number: str):
        capmonster = RecaptchaV2Task(self.capmonster_api_key)
        task_id = capmonster.create_task("https://www.fbsbx.com/captcha/recaptcha/iframe", "6Lc9qjcUAAAAADTnJq5kJMjN9aD1lxpRLMnCS2TR")
        captcha_token = capmonster.join_task_result(task_id)["gRecaptchaResponse"]

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://web.facebook.com/contacts/removal",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        variables = json.dumps({
            "input": {
                "contactpoint": number,
                "contactpoint_type": "LANDLINE",
                "platform": ["FB_AND_MSGER"],
                "solution_token": captcha_token
            }
        })
        body = {
            "variables": variables,
            "doc_id": "7250495224992687",
            "fb_dtsg": self._fb_dtsg
        }
        # body = f"variables={urllib.parse.quote(variables)}&doc_id=7250495224992687&fb_dtsg={urllib.parse.quote(self._fb_dtsg)}"
        r = self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        data = r.json()["data"]
        status = data["xfb_contact_removal_send_confirmation_code"]
        if status != "SUCCEED":
            raise Exception(status)

    def call_v2(self, number: str, country_code: str):
        if not self._ad_act_id:
            self._refresh_ad_act_id()

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://adsmanager.facebook.com/adsmanager/manage/accounts",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        variables = json.dumps({
            "input": {
                "authenticatable_entity_id": self._ad_act_id,
                "business_verification_ui_type": "ADS_MANAGER_ACCOUNT_OVERVIEW_SYD",
                "fev_wizard_product": "ADVERTISER_VETTING_VERIFICATION",
                "location": "BUSINESS_VERIFICATION_ADVERTISER_VERIFICATION_WIZARD",
                "trigger_event_type": "DIRECT_OPEN_BUSINESS_VERIFICATION_WIZARD_ADVERTISER_VERIFICATION",
                "nt_context": None,
                "trigger_session_id": str(uuid.uuid4())
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "10055075961232407",
            "fb_dtsg": self._fb_dtsg
        }
       #  body = f"variables={urllib.parse.quote(variables)}&doc_id=10055075961232407&fb_dtsg={urllib.parse.quote(self._fb_dtsg)}"
        r = self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_business_verification_advertiser_verification_wizard_trigger"]["screen"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "bv_wizard_advertiser_verification_enter_phone": {
                    "country_code": country_code,
                    "locale": "ar_AR",
                    "phone_number": number,
                    "serialized_state": serialized_state
                },
                "actor_id": self.cookies.get("c_user"),
                "client_mutation_id": "4"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6992119570822687",
            "fb_dtsg": self._fb_dtsg
        }
        # body = f"variables={urllib.parse.quote(variables)}&doc_id=6992119570822687&fb_dtsg={urllib.parse.quote(self._fb_dtsg)}"
        r = self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "challenge_select": {
                    "selected_challenge_method": "ROBOCALL",
                    "serialized_state": serialized_state
                },
                "actor_id": self.cookies.get("c_user"),
                "client_mutation_id": "5"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6992119570822687",
            "fb_dtsg": self._fb_dtsg
        }
        # body = f"variables={urllib.parse.quote(variables)}&doc_id=6992119570822687&fb_dtsg={urllib.parse.quote(self._fb_dtsg)}"
        r = self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
        if not r.json()["data"]["ixt_screen_next"]:
            raise Exception("PHONE_VERIFICATION_FAILED")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()
