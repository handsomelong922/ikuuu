# -*- coding: utf-8 -*-
import json
import requests
import os

# 账户
EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["PASSWORD"]
DOMAIN = os.environ["DOMAIN"]

# PushPlus 配置（至少需要 PUSHPLUS_TOKEN）
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]
PUSHPLUS_TOPIC = os.getenv("PUSHPLUS_TOPIC", "").strip()       # 可选：群组编码 topic
PUSHPLUS_TO = os.getenv("PUSHPLUS_TO", "").strip()             # 可选：好友令牌 to（与 topic 二选一）
PUSHPLUS_TEMPLATE = os.getenv("PUSHPLUS_TEMPLATE", "markdown") # 可选：html / markdown / json 等


class SSPANEL:
    name = "SSPANEL"

    def __init__(self, check_item):
        self.check_item = check_item
        self.pushplus_token = PUSHPLUS_TOKEN
        self.pushplus_topic = PUSHPLUS_TOPIC
        self.pushplus_to = PUSHPLUS_TO
        self.pushplus_template = PUSHPLUS_TEMPLATE

    def message2pushplus(self, title: str, content: str):
        print("PushPlus 消息推送开始")

        # PushPlus 参数：token 必填；content 必填；topic/to 可选（不建议同时填）0
        data = {
            "token": self.pushplus_token,
            "title": title,
            "content": content,
            "template": self.pushplus_template,
        }

        # 优先使用 to（好友消息）；否则使用 topic（群组）；都不填则发给自己 1
        if self.pushplus_to:
            data["to"] = self.pushplus_to
        elif self.pushplus_topic:
            data["topic"] = self.pushplus_topic

        try:
            resp = requests.post(
                "https://www.pushplus.plus/send",
                data=json.dumps(data),
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            # pushplus 返回 code=200 代表服务端收到请求；不等于最终发送必达（文档对 batchSend 明确说明，send 亦同理建议按返回信息判断）2
            result = resp.json()
            if result.get("code") != 200:
                print(f"PushPlus 推送失败: {result}")
            else:
                print("PushPlus 推送请求已提交")
        except Exception as e:
            print(f"PushPlus 推送异常: {e}")

    def sign(self, email, password, url):
        email = email.replace("@", "%40")
        try:
            session = requests.session()
            session.get(url=url, verify=False)
            login_url = url + "/auth/login"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            post_data = ("email=" + email + "&passwd=" + password + "&code=").encode()
            session.post(login_url, post_data, headers=headers, verify=False)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
                "Referer": url + "/user",
            }
            response = session.post(url + "/user/checkin", headers=headers, verify=False)
            msg = response.json().get("msg")
        except Exception:
            msg = "签到失败"
        return msg

    def main(self):
        email = self.check_item.get("email")
        password = self.check_item.get("password")
        url = self.check_item.get("url")

        sign_msg = self.sign(email=email, password=password, url=url)

        msg_lines = [
            {"name": "帐号信息", "value": email},
            {"name": "签到信息", "value": f"{sign_msg}"},
        ]
        msg = "\n".join([f"{one.get('name')}: {one.get('value')}" for one in msg_lines])

        self.message2pushplus(title="ikuuu 签到通知", content=msg)
        return msg


if __name__ == "__main__":
    _check_item = {"email": EMAIL, "password": PASSWORD, "url": DOMAIN}
    SSPANEL(check_item=_check_item).main()
