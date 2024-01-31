from facebook_py import Facebook
import json


with Facebook() as fb:
    fb.login(session=json.dumps({'fr': '0MrXPdIeyIRSOgtkK.AWWrB2kBalDXPRQZugRGK0OtHWs.Blul1W.Tj.AAA.0.0.Blul1W.AWUTEcTJvtQ', 'sb': 'Vl26ZQ0PCD-_9LDABJhYaEmY', 'c_user': '61556142117202', 'xs': '29%3AgJksDVqAW--K1w%3A2%3A1706712407%3A-1%3A-1', 'datr': 'Vl26ZahaWjvLMUSN_pMFZvQK'}))
    fb.verify()
