# -*- coding: utf-8 -*-
import json
import os
import re
import requests

# 账户（必填）
EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["PASSWORD"]
DOMAIN = os.environ["DOMAIN"]

# PushPlus（建议必填；未配置则跳过推送，不让脚本直接崩）
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "").strip()

# PushPlus（可选：二选一；都不填=发给自己）
PUSHPLUS_TOPIC = os.getenv("PUSHPLUS_TOPIC", "").strip()   # 群组编码 topic
PUSHPLUS_TO = os.getenv("PUSHPLUS_TO", "").strip()         # 好友令牌 to

# PushPlus（可选）
PUSHPLUS_TEMPLATE = os.getenv("PUSHPLUS_TEMPLATE", "markdown").strip()  # html / markdown / json 等


class SSPANEL:
    name = "SSPANEL"

    def __init__(self, check_item: dict):
        self.check_item = check_item
        self.pushplus_token = PUSHPLUS_TOKEN
        self.pushplus_topic = PUSHPLUS_TOPIC
        self.pushplus_to = PUSHPLUS_TO
        self.pushplus_template = PUSHPLUS_TEMPLATE

    def message2pushplus(self, title: str, content: str) -> None:
        if not self.pushplus_token:
            print("未配置 PUSHPLUS_TOKEN，已跳过 PushPlus 推送。")
            return

        print("PushPlus 消息推送开始")

        payload = {
            "token": self.pushplus_token,
            "title": title,
            "content": content,
            "template": self.pushplus_template,
        }

        # 优先 to，其次 topic；两者都不填则默认发给自己
        if self.pushplus_to:
            payload["to"] = self.pushplus_to
        elif self.pushplus_topic:
            payload["topic"] = self.pushplus_topic

        try:
            resp = requests.post(
                "https://www.pushplus.plus/send",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            result = resp.json()
            if result.get("code") != 200:
                print(f"PushPlus 推送失败：{result}")
            else:
                print("PushPlus 推送请求已提交")
        except Exception as e:
            print(f"PushPlus 推送异常：{e}")

    def sign(self, email: str, password: str, url: str) -> str:
        email = email.replace("@", "%40")
        try:
            session = requests.session()
            session.get(url=url, verify=False, timeout=15)

            login_url = url.rstrip("/") + "/auth/login"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            post_data = ("email=" + email + "&passwd=" + password + "&code=").encode()
            session.post(login_url, data=post_data, headers=headers, verify=False, timeout=15)

            headers = {"User-Agent": "Mozilla/5.0", "Referer": url.rstrip("/") + "/user"}
            response = session.post(url.rstrip("/") + "/user/checkin", headers=headers, verify=False, timeout=15)

            try:
                msg = response.json().get("msg") or "签到接口返回为空"
            except Exception:
                msg = f"签到接口非JSON返回，HTTP {response.status_code}"
        except Exception:
            msg = "签到失败"
        return msg

    @staticmethod
    def build_title_from_sign_msg(sign_msg: str, max_len: int = 40) -> str:
        """
        标题完全由 sign_msg 驱动：
        1) 若能解析到“获得了 X MB/GB...流量” => ikuuu 签到获得XMB流量（突出流量）
        2) 否则 => ikuuu 签到：{sign_msg}（直接反映实际返回，例如重复签到/失败）
        并对标题做长度截断，避免过长。
        """
        # 规范化：去掉换行、多余空格
        raw = (sign_msg or "").strip()
        raw_one_line = re.sub(r"\s+", " ", raw)

        # 提取流量（尽量宽松兼容：你获得了 1891 MB流量 / 获得了1891MB 流量 / 获得 1.5GB 流量）
        m = re.search(r"获得(?:了)?\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGTP]?B)\s*流量?", raw_one_line, flags=re.I)
        if m:
            amount = m.group(1)
            unit = m.group(2).upper()
            title = f"ikuuu 签到获得{amount}{unit}流量"
        else:
            # 不做预设：直接用实际返回内容作为标题后半段
            title = f"ikuuu 签到：{raw_one_line or '无返回信息'}"

        # 截断（PushPlus 标题过长可读性差）
        if len(title) > max_len:
            title = title[: max_len - 1] + "…"
        return title

    def main(self) -> str:
        email = self.check_item.get("email")
        password = self.check_item.get("password")
        url = self.check_item.get("url")

        sign_msg = self.sign(email=email, password=password, url=url)

        # 标题：由实际签到返回内容决定
        title = self.build_title_from_sign_msg(sign_msg)

        # 内容：保持不变
        msg_items = [
            {"name": "帐号信息", "value": email},
            {"name": "签到信息", "value": sign_msg},
        ]
        msg = "\n".join([f"{one['name']}: {one['value']}" for one in msg_items])

        self.message2pushplus(title=title, content=msg)
        return msg


if __name__ == "__main__":
    _check_item = {"email": EMAIL, "password": PASSWORD, "url": DOMAIN}
    SSPANEL(check_item=_check_item).main()
