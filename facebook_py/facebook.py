import json
import httpx
from bs4 import BeautifulSoup
from capmonster_python import RecaptchaV2Task
import time
import uuid
import re
from fake_useragent import FakeUserAgent


class Facebook:
    def __init__(self, capmonster_api_key: str = None, proxy: str = None):
        self._proxy = proxy
        self._fb_dtsg = None
        self._ad_act_id = None
        self._business_id = None
        self._serialized_state = None
        self._capmonster_api_key = capmonster_api_key
        self.session = None
        self._client = httpx.AsyncClient(
            proxies=f"http://{self._proxy}" if self._proxy else None,
            timeout=httpx.Timeout(10, read=30),
            follow_redirects=True
        )
        ua = FakeUserAgent(browsers="chrome", platforms="pc")
        user_agent = ua.random
        if user_agent.endswith(" "):
            user_agent = user_agent[:-1]
        self._client.headers.update({
            # "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": user_agent
        })

    async def _refresh_fb_dtsg(self):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        r = await self._client.get("https://web.facebook.com/&", headers=headers)
        if "checkpoint" in str(r.url):
            raise Exception("CHECKPOINT")
        try:
            self._fb_dtsg = re.search(r'"DTSGInitialData":{"token":"(.*?)"', r.text).group(1)
        except Exception:
            raise Exception("LOGIN_FAILED")

    async def _refresh_ad_act_id(self):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        r = await self._client.get("https://adsmanager.facebook.com/adsmanager/manage/accounts", headers=headers)
        self._ad_act_id = re.search(r"act=(\d+)", r.text).group(1)

    async def _refresh_business_id(self):
        headers = {
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        r = await self._client.get("https://business.facebook.com/home/accounts", headers=headers)
        self._business_id = re.search(r"business_id=(\d+)", r.text).group(1)

    async def login(self, username: str = None, password: str = None, session: dict = None):
        if username and password:
            headers = {
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1"
            }
            r = await self._client.get("https://web.facebook.com/", headers=headers)
            privacy_mutation_token = re.search(r'privacy_mutation_token=(.*?)"', r.text).group(1)
            self._client.cookies.update({"datr": re.search(r'"_js_datr","(.*?)"', r.text).group(1)})
            soup = BeautifulSoup(r.text, "html.parser")
            lsd = soup.find("input", {"name": "lsd"}).get("value")
            jazoest = soup.find("input", {"name": "jazoest"}).get("value")

            headers = {
                "Referer": "https://web.facebook.com/",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
            }
            body = {
                "jazoest": jazoest,
                "lsd": lsd,
                "email": username,
                "login_source": "comet_headerless_login",
                "next": "",
                "encpass": f"#PWD_BROWSER:0:{round(time.time())}:{password}",
            }
            r = await self._client.post(f"https://web.facebook.com/login/?privacy_mutation_token={privacy_mutation_token}", headers=headers, data=body, follow_redirects=False)
            if "c_user" not in dict(r.cookies) or "xs" not in dict(r.cookies):
                raise Exception("LOGIN_FAILED")

            self.session = dict(self._client.cookies)
        if session:
            self.session = json.loads(session)
            self._client.cookies.update(self.session)

        await self._refresh_fb_dtsg()

    async def like(self, url: str):
        headers = {
                "Referer": "https://web.facebook.com/",
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
        }
        r = await self._client.get(url, headers=headers)
        feedback_id = re.search(r'Plugin","feedback_id":"(.*?)"', r.text).group(1)

        headers = {
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
        r = await self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        if not r.json()["data"]["feedback_react"]:
            raise Exception("LIKE_FAILED")

    async def comment(self, url: str, text: str):
        headers = {
                "Referer": "https://web.facebook.com/",
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
        }
        r = await self._client.get(url, headers=headers)
        feedback_id = re.search(r'Plugin","feedback_id":"(.*?)"', r.text).group(1)

        headers = {
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
        r = await self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        if not r.json()["data"]["comment_create"]:
            raise Exception("COMMENT_FAILED")

    async def verify(self, user):
        headers = {
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        variables = json.dumps({
            "input": {
                "client_mutation_id": "1",
                "actor_id": self.session.get("c_user"),
                "business_name": user.get_full_name(),
                "first_name": user.get_first_name(),
                "last_name": user.get_last_name(),
                "email_address": f"{user.get_username()}@gmail.com",
                "creation_source": "WHATSAPP_BUSINESS_API_EMBEDDED_SIGNUP",
                "entry_point": "WHATSAPP_BUSINESS_ONBOARDING_EMBEDDED_SIGNUP_BUSINESS_ACCOUNT",
                "business_profile": {
                    "legal_name": user.get_full_name(),
                    "website": f"https://{user.get_username()}.com",
                    "address": {
                        "country": user.get_nat()
                    }
                },
                "app_id": "1593811571129902",
                "log_session_id": str(uuid.uuid4())
            }
        })
        body = {
            "variables": variables,
            "doc_id": "6941155049285267",
            "fb_dtsg": self._fb_dtsg
        }
        r = await self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        r.raise_for_status()
        business_id = r.json()["data"]["xfb_create_meta_business_account"]["id"]

        variables = json.dumps({
            "input": {
                "client_mutation_id": "2",
                "actor_id": self.session.get("c_user"),
                "app_id": "1593811571129902",
                "log_session_id": str(uuid.uuid4()),
                "business_id": business_id,
                "api_account_type": "EMBEDDED_SIGNUP",
                "creation_source": "EMBEDDED_SIGNUP",
                "friendly_name": "Mehdi",
                "timezone_id": 1,
                "currency": None,
                "primary_funding_source": None,
                "purchase_order_number": None,
                "on_behalf_of_business_id": None,
                "partner_business_id": 235609652134321,
                "page_id": None,
                "product": "EMBEDDED_SIGNUP"
            }
        })
        body = {
            "variables": variables,
            "doc_id": "6810325559007017",
            "fb_dtsg": self._fb_dtsg
        }
        r = await self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        r.raise_for_status()

    async def contact(self, number: str, sms: bool = False):
        capmonster = RecaptchaV2Task(self._capmonster_api_key)
        task_id = capmonster.create_task("https://www.fbsbx.com/captcha/recaptcha/iframe", "6Lc9qjcUAAAAADTnJq5kJMjN9aD1lxpRLMnCS2TR")
        captcha_token = capmonster.join_task_result(task_id)["gRecaptchaResponse"]

        headers = {
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
        r = await self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        data = r.json()["data"]
        status = data["xfb_contact_removal_send_confirmation_code"]
        if status != "SUCCEED":
            raise Exception(status)

    async def contact_v2(self, number: str, country_code: str, sms: bool = False):
        if not self._ad_act_id:
            await self._refresh_ad_act_id()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://adsmanager.facebook.com/adsmanager/manage/accounts",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if not self._serialized_state:
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
            r = await self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
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
            r = await self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
            self._serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "challenge_select": {
                    "selected_challenge_method": "SMS" if sms else "ROBOCALL",
                    "serialized_state": self._serialized_state
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
        r = await self._client.post("https://adsmanager.facebook.com/api/graphql", headers=headers, data=body)
        if not r.json()["data"]["ixt_screen_next"]:
            raise Exception("PHONE_VERIFICATION_FAILED")

    async def contact_v3(self, number: str, country_code: str, user, sms: bool = False):
        if not self._business_id:
            await self._refresh_business_id()

        headers = {
            "Referer": "https://business.facebook.com/settings/security",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if not self._serialized_state:
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
            r = await self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
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
            r = await self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
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
            r = await self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
            serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

            variables = json.dumps({
                "input": {
                    "bv_wizard_business_details_primary": {
                        "city": user.get_city(),
                        "email": "",
                        "legal_name": user.get_full_name(),
                        "phone_number": number,
                        "postal_code": user.get_postcode(),
                        "social_credit_number": "",
                        "social_media_url": f"https://{user.get_username()}.com",
                        "state": user.get_state(),
                        "street_1": user.get_street(),
                        "street_2": "",
                        "tax_id_number": "",
                        "website_url": f"https://{user.get_username()}.com",
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
            r = await self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
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
            r = await self._client.post("https://business.facebook.com/api/graphql", headers=headers, data=body)
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
            r = await self._client.post("https://business.facebook.com/api/graphql/", headers=headers, data=body)
            self._serialized_state = r.json()["data"]["ixt_screen_next"]["view_model"]["serialized_state"]

        variables = json.dumps({
            "input": {
                "advertiser_authenticity_confirm_phone_number": {
                    "locale": "ar_AR",
                    "phone_number": number,
                    "serialized_state": self._serialized_state
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
        r = await self._client.post("https://business.facebook.com/api/graphql/", headers=headers, data=body)
        if not r.json()["data"]["ixt_screen_next"]:
            raise Exception("PHONE_VERIFICATION_FAILED")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()
