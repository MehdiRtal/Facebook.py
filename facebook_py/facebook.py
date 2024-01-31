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

    def verify(self):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            # "Referer": "https://web.facebook.com/v16.0/dialog/oauth?encrypted_query_string=AeDfBkldn5Udsdf1e4ByFQe9Y6oqv0A9acLWYfNjpeKj-X-kjYnY6djId_U1GX8EQ-ybdu7BzICrbLNl54y-irrnRxWPzMwWCDIhrUbB_mg79UdUyuWVhl46qa99uaRGU7J-ZjCXe8eTatcm3_O0Sb_IibuR67bV62e2u8C-Jy5W-4ucz9XhbHnr7WYsAbFtrP-_xxm1xt9yRSmwokr2BEubMlHAlGTHuqoTzlOYOT2qCgNq5ZbdqA3rGVN6NGjtS013I6IPA7ET7m8E6RY-rdK8MSY943W10gdfPotXewJktGtFqYnFk2dD3eHZ634RU1t3GplvEo5AQO4-L4FqzOnEj9fdsa1GQ-gONvYRkIM7BFN2yNDCCTkvAE_WBaQk3IBes06HbSLGTmqdFeHMqBUOdHyqnxUSBg3RP3bujA3SyA7TLStiwVUkyAeVdsMRvY5HsuOm3CBZBi8p4G73x2aOonh6g1Q1oOE2BaOijIqe7ZWXF6pGtNLNCPHvY0bhvKFpSVYYCLxvlL0mNOPY_yM1qu3q43gqBQjOCPlRVSYm2JGQdXR8-Ck3ReInS16tA25FVRaf7YYzugEn0yF84eRmg4qQ5sJC0vyyCB2EmyumL4wTjKSEAqstPhBG7R-XIR8Txipf80_5aHJMdvttOGoD8fTuNbohHoQ_8EEHmK1x5GKqT-kdu8Tf41Kb4edQ_u3UykCy97efbna2c6kpWW003RMydgtBejEJPw3uZT-5NzllznF6zInz_VzHyeBlelCDF_m3MQ1Hb-JCp2vSAVLpUzR_9FDWNTCX6M6RdMY-pBjVjqhf_4nH0FRDDS7wINuPGW0hyLF4-YC-2M_YC4amHF-uYvD82pQCPtW1qVaZueLZs6YjnTShocrHsU5Hcaf8N8x8Ggypeo9wqh8z9XiEVrxDuc0YFz-za1EE-LLQEFjuOef-ZXc_BfVzERJ9-cvb4_vQsKT2KeyaucS2IKGhhUVbFjoroWB-ToOa5mZit3BOE2yzIUuWkLZXw8t8V4ASRksRvLMP9j0yN39xSXt4_I63AYEaHafHVs4Mvbmmljf74htfK7yYTbZ9u6iJug0gc18E3KSWhhfBvDIilxfQe-5M1ObMxBlav1pYH2NRxL5XCs9yHta7Benn7ED2mJ2bUmgEq0LD3uyId2uWFSA1FWKkWt2SDFNQGYeVUFUHxBRwbDTdcmNtXQCzAy3lBd6boakpIXCPknm6k64zVX_KzYbGZmM057Ol4hj3cj_mHN2Un7nj2Zd3z3Zu5EgdBPz72XB01BRc5KxCi3odYhZwXlrl4dAlFt7NHiI2WDAoddF2ZLSWKXb5CaBsX5WMxris0P-C5WOtRvcq6rIjQh_wt7gTSeFr-FHccpifiBJSXa-LOH7G3VEJ5-slKWSEjl2M9etvyinRDeMv7loSR5YQnvQROX33usWYQTjLW8ykTWFrXf6FS2791QW6d1Z8rW20ufZ8ZzQSZOae0l_7K-iSy-Vvp67lW-Xnm0QinuLlK8H60hobZBVIjgVRfrghexs2Gl74tS-5fHcmRXRDCplitimj15UV-9JHlxKWaUTIzAG309wvxNZL2AvJ2fAx5RnxhtWuVSpJIV-CTpSCgAsAZyg9luCmn12BWTwE1SWTzradNdOB1BEBrboI4SdpKbqC-XXi81kwklK2gHOFZUAy0qBiebHsJTipqIfWfIntgqAltDh-hOdIRrcuLhnfi6pNuV-RT1ytIwsDNNcVju4AVokZr-Hn8WCFNnwetx_SPqhkSWlsccyMkye2RKm4M4zrOkWG09vC-_1Qukkt5UdHSUn4JSwu9-D9t4UUX3JfukwEZ0M_jvnJ87_TGPuxVrWakcVZKr8ElnE1tBLOwGSjTZbCAUe56iIYxLMGiHnHiE_u7jXQoJJ-DI03HoUEA-VNXOiU5bW0Gdj59kSxa1jbmbWleQ7z8jeTMXWRaVoeHOx-HoOOHkuUABoyYoujS9_Cx6h3g9LltY15yN68OpwWFInwVD2wAEvHfvHa8VZZgwSAUJhrWFMx2Zq4cbt81cY3w45ovWm4y7vVm94zlkt9l_91SmHNoIg&_rdc=1&_rdr",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        variables = json.dumps({"input":{"app_id":"1593811571129902","log_session_id":"72aaacdd-974e-4d92-8305-b81eaa095372","partner_business_id":235609652134321,"preverified_phone_number_ids":None}})
        body = {
            "variables": variables,
            "doc_id": "8639807102758777",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        print(r.json())

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            # "Referer": "https://web.facebook.com/v16.0/dialog/oauth?encrypted_query_string=AeDfBkldn5Udsdf1e4ByFQe9Y6oqv0A9acLWYfNjpeKj-X-kjYnY6djId_U1GX8EQ-ybdu7BzICrbLNl54y-irrnRxWPzMwWCDIhrUbB_mg79UdUyuWVhl46qa99uaRGU7J-ZjCXe8eTatcm3_O0Sb_IibuR67bV62e2u8C-Jy5W-4ucz9XhbHnr7WYsAbFtrP-_xxm1xt9yRSmwokr2BEubMlHAlGTHuqoTzlOYOT2qCgNq5ZbdqA3rGVN6NGjtS013I6IPA7ET7m8E6RY-rdK8MSY943W10gdfPotXewJktGtFqYnFk2dD3eHZ634RU1t3GplvEo5AQO4-L4FqzOnEj9fdsa1GQ-gONvYRkIM7BFN2yNDCCTkvAE_WBaQk3IBes06HbSLGTmqdFeHMqBUOdHyqnxUSBg3RP3bujA3SyA7TLStiwVUkyAeVdsMRvY5HsuOm3CBZBi8p4G73x2aOonh6g1Q1oOE2BaOijIqe7ZWXF6pGtNLNCPHvY0bhvKFpSVYYCLxvlL0mNOPY_yM1qu3q43gqBQjOCPlRVSYm2JGQdXR8-Ck3ReInS16tA25FVRaf7YYzugEn0yF84eRmg4qQ5sJC0vyyCB2EmyumL4wTjKSEAqstPhBG7R-XIR8Txipf80_5aHJMdvttOGoD8fTuNbohHoQ_8EEHmK1x5GKqT-kdu8Tf41Kb4edQ_u3UykCy97efbna2c6kpWW003RMydgtBejEJPw3uZT-5NzllznF6zInz_VzHyeBlelCDF_m3MQ1Hb-JCp2vSAVLpUzR_9FDWNTCX6M6RdMY-pBjVjqhf_4nH0FRDDS7wINuPGW0hyLF4-YC-2M_YC4amHF-uYvD82pQCPtW1qVaZueLZs6YjnTShocrHsU5Hcaf8N8x8Ggypeo9wqh8z9XiEVrxDuc0YFz-za1EE-LLQEFjuOef-ZXc_BfVzERJ9-cvb4_vQsKT2KeyaucS2IKGhhUVbFjoroWB-ToOa5mZit3BOE2yzIUuWkLZXw8t8V4ASRksRvLMP9j0yN39xSXt4_I63AYEaHafHVs4Mvbmmljf74htfK7yYTbZ9u6iJug0gc18E3KSWhhfBvDIilxfQe-5M1ObMxBlav1pYH2NRxL5XCs9yHta7Benn7ED2mJ2bUmgEq0LD3uyId2uWFSA1FWKkWt2SDFNQGYeVUFUHxBRwbDTdcmNtXQCzAy3lBd6boakpIXCPknm6k64zVX_KzYbGZmM057Ol4hj3cj_mHN2Un7nj2Zd3z3Zu5EgdBPz72XB01BRc5KxCi3odYhZwXlrl4dAlFt7NHiI2WDAoddF2ZLSWKXb5CaBsX5WMxris0P-C5WOtRvcq6rIjQh_wt7gTSeFr-FHccpifiBJSXa-LOH7G3VEJ5-slKWSEjl2M9etvyinRDeMv7loSR5YQnvQROX33usWYQTjLW8ykTWFrXf6FS2791QW6d1Z8rW20ufZ8ZzQSZOae0l_7K-iSy-Vvp67lW-Xnm0QinuLlK8H60hobZBVIjgVRfrghexs2Gl74tS-5fHcmRXRDCplitimj15UV-9JHlxKWaUTIzAG309wvxNZL2AvJ2fAx5RnxhtWuVSpJIV-CTpSCgAsAZyg9luCmn12BWTwE1SWTzradNdOB1BEBrboI4SdpKbqC-XXi81kwklK2gHOFZUAy0qBiebHsJTipqIfWfIntgqAltDh-hOdIRrcuLhnfi6pNuV-RT1ytIwsDNNcVju4AVokZr-Hn8WCFNnwetx_SPqhkSWlsccyMkye2RKm4M4zrOkWG09vC-_1Qukkt5UdHSUn4JSwu9-D9t4UUX3JfukwEZ0M_jvnJ87_TGPuxVrWakcVZKr8ElnE1tBLOwGSjTZbCAUe56iIYxLMGiHnHiE_u7jXQoJJ-DI03HoUEA-VNXOiU5bW0Gdj59kSxa1jbmbWleQ7z8jeTMXWRaVoeHOx-HoOOHkuUABoyYoujS9_Cx6h3g9LltY15yN68OpwWFInwVD2wAEvHfvHa8VZZgwSAUJhrWFMx2Zq4cbt81cY3w45ovWm4y7vVm94zlkt9l_91SmHNoIg&_rdc=1&_rdr",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        variables = json.dumps({})
        body = {
            "variables": variables,
            "doc_id": "8639807102758777",
            "fb_dtsg": self._fb_dtsg
        }
        r = self._client.post("https://web.facebook.com/api/graphql", headers=headers, data=body)
        print(r.json())

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
