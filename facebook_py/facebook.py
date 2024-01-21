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
        self.session = None
        self._fb_dtsg = None
        self._ad_act_id = None
        self._business_id = None
        self.capmonster_api_key = capmonster_api_key
        self._client = httpx.Client(
            proxies=f"http://{self._proxy}" if self._proxy else None,
            timeout=httpx.Timeout(5.0, read=30.0),
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
        except Exception:
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

    def _refresh_business_id(self):
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
        r = self._client.get("https://business.facebook.com/home/accounts", headers=headers)
        self._business_id = re.search(r"business_id=(\d+)", r.text).group(1)

    def login(self, username: str = None, password: str = None, session: dict = None):
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

            self.session = dict(self._client.cookies)
        if session:
            self.session = json.loads(session)
            self._client.cookies.update(self.session)

        self._refresh_fb_dtsg()

    def like(self, url: str):
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
        r = self._client.get(url, headers=headers)
        feedback_id = re.search(r'Plugin","feedback_id":"(.*?)"', r.text).group(1)

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
            "input": {
                "attribution_id_v2": "CometPhotoRoot.react,comet.mediaviewer.photo,via_cold_start,1698400320438,739435,,",
                "feedback_id": feedback_id,
                "feedback_reaction_id": "1635855486666999",
                "feedback_source": "MEDIA_VIEWER",
                "is_tracking_encrypted": True,
                "tracking": [],
                "session_id": str(uuid.uuid4()),
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "useDefaultActor": False,
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6623712531077310",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        if not r.json()["data"]["feedback_react"]:
            raise Exception("LIKE_FAILED")

    def comment(self, url: str, text: str):
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
        r = self._client.get(url, headers=headers)
        feedback_id = re.search(r'Plugin","feedback_id":"(.*?)"', r.text).group(1)

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
            "displayCommentsFeedbackContext": None,
            "displayCommentsContextEnableComment": None,
            "displayCommentsContextIsAdPreview": None,
            "displayCommentsContextIsAggregatedShare": None,
            "displayCommentsContextIsStorySet": None,
            "feedLocation":"COMET_MEDIA_VIEWER",
            "feedbackSource": 65,
            "focusCommentID": None,
            "groupID": None,
            "includeNestedComments": False,
            "input":{
                "attachments": None,
                "feedback_id": feedback_id,
                "formatting_style": None,
                "message":{
                    "ranges": [],
                    "text": text
                },
                "reply_target_clicked": False,
                "attribution_id_v2": "CometPhotoRoot.react,comet.mediaviewer.photo,via_cold_start,1698403740008,170402,,",
                "is_tracking_encrypted": True,
                "tracking": ["{\"assistant_caller\":\"comet_above_composer\",\"conversation_guide_session_id\": None,\"conversation_guide_shown\": None}"],
                "feedback_source": "MEDIA_VIEWER",
                "idempotence_token": f"client:{str(uuid.uuid4())}",
                "session_id": str(uuid.uuid4()),
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "inviteShortLinkKey": None,
            "renderLocation": None,
            "scale": 1,
            "useDefaultActor": False,
            "UFI2CommentsProvider_commentsKey": "CometPhotoRootQuery"
        })
        body = {
            "variables": variables,
            "doc_id": "6104498286317023",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        if not r.json()["data"]["comment_create"]:
            raise Exception("COMMENT_FAILED")

    def contact(self, number: str, sms: bool = False):
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
                "contactpoint_type": "PHONE" if sms else "LANDLINE",
                "platform": ["FB_AND_MSGER"],
                "solution_token": captcha_token
            }
        })
        body = {
            "variables": variables,
            "doc_id": "7250495224992687",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        data = r.json()["data"]
        status = data["xfb_contact_removal_send_confirmation_code"]
        if status != "SUCCEED":
            raise Exception(status)

    def contact_v2(self, number: str, country_code: str, sms: bool = False):
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
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6992119570822687",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "challenge_select": {
                    "selected_challenge_method": "SMS" if sms else "ROBOCALL",
                    "serialized_state": serialized_state
                },
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6992119570822687",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
        if not r.json()["data"]["ixt_screen_next"]:
            raise Exception("PHONE_VERIFICATION_FAILED")

    def contact_v3(self, number: str, country_code: str, sms: bool = False):
        if not self._business_id:
            self._refresh_business_id()

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://business.facebook.com/settings/security",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        variables = json.dumps({
            "input":{
                "business_id": self._business_id,
                "business_verification_ui_type": "BUSINESS_MANAGER_COMET",
                "fev_wizard_product": "CLASSIC_BV",
                "location": "BUSINESS_VERIFICATION_WIZARD",
                "trigger_event_type": "DIRECT_OPEN_BUSINESS_VERIFICATION_WIZARD",
                "nt_context": None,
                "trigger_session_id": str(uuid.uuid4())
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6817224355039434",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_business_verification_wizard_trigger"]["screen"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "bv_wizard_overview": {
                    "serialized_state": serialized_state
                },
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6615289768568483",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "bv_wizard_country_selection": {
                    "country_code": country_code,
                    "serialized_state": serialized_state
                },
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6615289768568483",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "bv_wizard_business_details_primary": {
                    "city": ".",
                    "email": "",
                    "legal_name": ".",
                    "phone_number": number,
                    "postal_code": ".",
                    "social_credit_number": "",
                    "social_media_url": "google.com",
                    "state": ".",
                    "street_1": ".",
                    "street_2": ".",
                    "tax_id_number": "",
                    "website_url": "google.com",
                    "serialized_state": serialized_state
                },
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6615289768568483",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "challenge_select": {
                    "selected_challenge_method": "SMS" if sms else "ROBOCALL",
                    "serialized_state": serialized_state
                },
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6615289768568483",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "bv_wizard_manual_flow_overview": {
                    "serialized_state": serialized_state
                },
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6615289768568483",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://business.facebook.com/api/graphql/", headers=headers, data=body)
        serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "advertiser_authenticity_confirm_phone_number": {
                    "locale": "ar_AR",
                    "phone_number": number,
                    "serialized_state": serialized_state
                },
                "actor_id": self.session.get("c_user"),
                "client_mutation_id": "0"
            },
            "scale": 1
        })
        body = {
            "variables": variables,
            "doc_id": "6615289768568483",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://business.facebook.com/api/graphql/", headers=headers, data=body)
        if not r.json()["data"]["ixt_screen_next"]:
            raise Exception("PHONE_VERIFICATION_FAILED")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()
