from facebook_py import Facebook
import json


with Facebook() as fb:
    fb.login(session=json.dumps({'ps_l': '0', 'ps_n': '0', 'fr': '08HHKF8BTuwghUGIe.AWXed7769IGehFlb-HXIZReJN2I.BluifL.iK.AAA.0.0.BluifL.AWVfNAuzAmw', 'sb': 'yye6ZT_auv395Xy_AHKuIU5G', 'c_user': '61556123128827', 'xs': '20%3AVcIyVn_iCyxFNg%3A2%3A1706698700%3A-1%3A-1', 'datr': 'yye6ZQqOkZreeB152IIx-I5t'}))
    fb.verify()
