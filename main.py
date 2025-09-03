# -*- coding: utf8 -*-
import math
import traceback
from datetime import datetime
import pytz

import json
import random
import re
import time
import os

import requests


# 获取北京时间
def get_beijing_time():
    target_timezone = pytz.timezone('Asia/Shanghai')
    # 获取当前时间
    return datetime.now().astimezone(target_timezone)


# 格式化时间
def format_now():
    return get_beijing_time().strftime("%Y-%m-%d %H:%M:%S")


# 获取默认值转int
def get_int_value_default(_config: dict, _key, default):
    _config.setdefault(_key, default)
    return int(_config.get(_key))


# 获取当前时间对应的最大和最小步数
def get_min_max_by_time(hour=None, minute=None):
    if hour is None:
        hour = time_bj.hour
    if minute is None:
        minute = time_bj.minute
    time_rate = min((hour * 60 + minute) / (22 * 60), 1)
    min_step = get_int_value_default(config, 'MIN_STEP', 18000)
    max_step = get_int_value_default(config, 'MAX_STEP', 25000)
    return int(time_rate * min_step), int(time_rate * max_step)


# 虚拟ip地址
def fake_ip():
    # 随便找的国内IP段：223.64.0.0 - 223.117.255.255
    return f"{223}.{random.randint(64, 117)}.{random.randint(0, 255)}.{random.randint(0, 255)}"


# 账号脱敏
def desensitize_user_name(user):
    if len(user) <= 8:
        ln = max(math.floor(len(user) / 3), 1)
        return f'{user[:ln]}***{user[-ln:]}'
    return f'{user[:3]}****{user[-4:]}'


# 获取时间戳
def get_time():
    current_time = get_beijing_time()
    return "%.0f" % (current_time.timestamp() * 1000)


# 获取登录code
def get_access_token(location):
    code_pattern = re.compile("(?<=access=).*?(?=&)")
    result = code_pattern.findall(location)
    if result is None or len(result) == 0:
        return None
    return result[0]


# pushplus消息推送
def push_plus(title, content):
    requestUrl = f"http://www.pushplus.plus/send"
    data = {
        "token": PUSH_PLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html",
        "channel": "wechat"
    }
    try:
        response = requests.post(requestUrl, data=data)
        if response.status_code == 200:
            json_res = response.json()
            print(f"pushplus推送完毕：{json_res['code']}-{json_res['msg']}")
        else:
            print("pushplus推送失败")
    except:
        print("pushplus推送异常")


class MiMotionRunner:
    def __init__(self, _user, _passwd):
        user = str(_user)
        password = str(_passwd)
        self.invalid = False
        self.log_str = ""
        if user == '' or password == '':
            self.error = "用户名或密码填写有误！"
            self.invalid = True
            pass
        self.password = password
        if ("+86" in user) or "@" in user:
            user = user
        else:
            user = "+86" + user
        if "+86" in user:
            self.is_phone = True
        else:
            self.is_phone = False
        self.user = user
        self.fake_ip_addr = fake_ip()
        self.log_str += f"创建虚拟ip地址：{self.fake_ip_addr}\n"

    # 登录
    def login(self):

        url1 = "https://api-user.huami.com/registrations/" + self.user + "/tokens"
        login_headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2",
            "X-Forwarded-For": self.fake_ip_addr
        }
        data1 = {
            "client_id": "HuaMi",
            "password": f"{self.password}",
            "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
            "token": "access"
        }
        r1 = requests.post(url1, data=data1, headers=login_headers, allow_redirects=False)
        if r1.status_code != 303:
            self.log_str += "登录异常，status: %d\n" % r1.status_code
            return 0, 0
        location = r1.headers["Location"]
        try:
            code = get_access_token(location)
            if code is None:
                self.log_str += "获取accessToken失败\n"
                return 0, 0
        except:
            self.log_str += f"获取accessToken异常:{traceback.format_exc()}\n"
            return 0, 0
        # print("access_code获取成功！")
        # print(code)

        url2 = "https://account.huami.com/v2/client/login"
        if self.is_phone:
            data2 = {
                "app_name": "com.xiaomi.hm.health",
                "app_version": "4.6.0",
                "code": f"{code}",
                "country_code": "CN",
                "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
                "device_model": "phone",
                "grant_type": "access_token",
                "third_name": "huami_phone",
            }
        else:
            data2 = {
                "allow_registration=": "false",
                "app_name": "com.xiaomi.hm.health",
                "app_version": "6.3.5",
                "code": f"{code}",
                "country_code": "CN",
                "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
                "device_model": "phone",
                "dn": "api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com",
                "grant_type": "access_token",
                "lang": "zh_CN",
                "os_version": "1.5.0",
                "source": "com.xiaomi.hm.health",
                "third_name": "email",
            }
        r2 = requests.post(url2, data=data2, headers=login_headers).json()
        login_token = r2["token_info"]["login_token"]
        # print("login_token获取成功！")
        # print(login_token)
        userid = r2["token_info"]["user_id"]
        # print("userid获取成功！")
        # print(userid)

        return login_token, userid

    # 获取app_token
    def get_app_token(self, login_token):
        url = f"https://account-cn.huami.com/v1/client/app_tokens?app_name=com.xiaomi.hm.health&dn=api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com&login_token={login_token}"
        headers = {'User-Agent': 'MiFit/5.3.0 (iPhone; iOS 14.7.1; Scale/3.00)', 'X-Forwarded-For': self.fake_ip_addr}
        response = requests.get(url, headers=headers).json()
        app_token = response['token_info']['app_token']
        # print("app_token获取成功！")
        # print(app_token)
        return app_token

    # 主函数
    def login_and_post_step(self, min_step, max_step):
        if self.invalid:
            return "账号或密码配置有误", False
        step = str(random.randint(min_step, max_step))
        self.log_str += f"已设置为随机步数范围({min_step}~{max_step}) 随机值:{step}\n"

        # 旧的 Huami/Zepp 提交接口已不可用，直接使用第三方 BugPK 提供的 Zepp API
        # API: https://api.bugpk.com/api/yd?username=Zepp账号&password=Zepp密码&step=88888
        try:
            api_user = self.user
            if api_user.startswith('+86'):
                api_user = api_user[3:]

            api_url = 'https://api.bugpk.com/api/yd'
            params = {'username': api_user, 'password': self.password, 'step': step}
            self.log_str += f"调用第三方步数接口：{api_url} params={params}\n"
            resp = requests.get(api_url, params=params, timeout=20)
        except Exception as e:
            self.log_str += f"调用第三方接口异常：{traceback.format_exc()}\n"
            return f"修改步数（{step}） 调用接口失败: {e}", False

        if resp.status_code != 200:
            self.log_str += f"接口返回HTTP错误：{resp.status_code} {resp.text}\n"
            return f"修改步数（{step}） HTTP错误：{resp.status_code}", False

        try:
            j = resp.json()
        except Exception:
            self.log_str += f"接口返回非JSON：{resp.text}\n"
            return f"修改步数（{step}） 接口返回非JSON：{resp.text}", False

        code = j.get('code')
        msg = j.get('msg') if j.get('msg') is not None else str(j)
        user_ret = j.get('user')
        step_ret = j.get('step')
        now = j.get('now')

        success = (int(code) == 200) if code is not None else False
        result_msg = f"{code}-{msg} user:{user_ret} step:{step_ret} now:{now}"
        self.log_str += f"接口返回：{result_msg}\n"
        return f"修改步数（{step}） 返回: {result_msg}", success


# 启动主函数
def push_to_push_plus(exec_results, summary):
    # 判断是否需要pushplus推送
    if PUSH_PLUS_TOKEN is not None and PUSH_PLUS_TOKEN != '' and PUSH_PLUS_TOKEN != 'NO':
        if PUSH_PLUS_HOUR is not None and PUSH_PLUS_HOUR.isdigit():
            if time_bj.hour != int(PUSH_PLUS_HOUR):
                print(f"当前设置push_plus推送整点为：{PUSH_PLUS_HOUR}, 当前整点为：{time_bj.hour}，跳过推送")
                return
        html = f'<div>{summary}</div>'
        if len(exec_results) >= PUSH_PLUS_MAX:
            html += '<div>账号数量过多，详细情况请前往github actions中查看</div>'
        else:
            html += '<ul>'
            for exec_result in exec_results:
                success = exec_result['success']
                if success is not None and success is True:
                    html += f'<li><span>账号：{exec_result["user"]}</span>刷步数成功，接口返回：{exec_result["msg"]}</li>'
                else:
                    html += f'<li><span>账号：{exec_result["user"]}</span>刷步数失败，失败原因：{exec_result["msg"]}</li>'
            html += '</ul>'
        push_plus(f"{format_now()} 刷步数通知", html)


def run_single_account(total, idx, user_mi, passwd_mi):
    idx_info = ""
    if idx is not None:
        idx_info = f"[{idx+1}/{total}]"
    log_str = f"[{format_now()}]\n{idx_info}账号：{desensitize_user_name(user_mi)}"
    try:
        runner = MiMotionRunner(user_mi, passwd_mi)
        exec_msg, success = runner.login_and_post_step(min_step, max_step)
        log_str += runner.log_str
        log_str += f'{exec_msg}\n'
        exec_result = {"user": user_mi, "success": success,
                       "msg": exec_msg}
    except:
        log_str += f"执行异常:{traceback.format_exc()}\n"
        log_str += traceback.format_exc()
        exec_result = {"user": user_mi, "success": False,
                       "msg": f"执行异常:{traceback.format_exc()}"}
    print(log_str)
    return exec_result


def execute():
    user_list = users.split('#')
    passwd_list = passwords.split('#')
    exec_results = []
    if len(user_list) == len(passwd_list):
        idx, total = 0, len(user_list)
        if use_concurrent:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                exec_results = executor.map(lambda x: run_single_account(total, x[0], *x[1]), enumerate(zip(user_list, passwd_list)))
        else:
            for user_mi, passwd_mi in zip(user_list, passwd_list):
                exec_results.append(run_single_account(total, idx, user_mi, passwd_mi))
                idx += 1
                if idx < total:
                    # 每个账号之间间隔一定时间请求一次，避免接口请求过于频繁导致异常
                    time.sleep(sleep_seconds)

        success_count = 0
        push_results = []
        for result in exec_results:
            push_results.append(result)
            if result['success'] is True:
                success_count += 1
        summary = f"\n执行账号总数{total}，成功：{success_count}，失败：{total - success_count}"
        print(summary)
        push_to_push_plus(push_results, summary)
    else:
        print(f"账号数长度[{len(user_list)}]和密码数长度[{len(passwd_list)}]不匹配，跳过执行")
        exit(1)


if __name__ == "__main__":
    # 北京时间
    time_bj = get_beijing_time()
    if os.environ.__contains__("CONFIG") is False:
        print("未配置CONFIG变量，无法执行")
        exit(1)
    else:
        # region 初始化参数
        config = dict()
        try:
            config = dict(json.loads(os.environ.get("CONFIG")))
        except:
            print("CONFIG格式不正确，请检查Secret配置，请严格按照JSON格式：使用双引号包裹字段和值，逗号不能多也不能少")
            traceback.print_exc()
            exit(1)
        PUSH_PLUS_TOKEN = config.get('PUSH_PLUS_TOKEN')
        PUSH_PLUS_HOUR = config.get('PUSH_PLUS_HOUR')
        PUSH_PLUS_MAX = get_int_value_default(config, 'PUSH_PLUS_MAX', 30)
        sleep_seconds = config.get('SLEEP_GAP')
        if sleep_seconds is None or sleep_seconds == '':
            sleep_seconds = 5
        sleep_seconds = float(sleep_seconds)
        users = config.get('USER')
        passwords = config.get('PWD')
        if users is None or passwords is None:
            print("未正确配置账号密码，无法执行")
            exit(1)
        min_step, max_step = get_min_max_by_time()
        use_concurrent = config.get('USE_CONCURRENT')
        if use_concurrent is not None and use_concurrent == 'True':
            use_concurrent = True
        else:
            print(f"多账号执行间隔：{sleep_seconds}")
            use_concurrent = False
        # endregion
        execute()
