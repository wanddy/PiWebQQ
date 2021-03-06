# -*- coding: utf-8 -*-

from HttpClient import HttpClient
import re, random, md5, json, os, time, thread, subprocess, logging


QQ = 10000
PASS = "PASS"

ClientID = 8534174
APPID = 1003903
PSessionID = ''

def getEncPass(q, p, v):
  m = md5.new(p).digest() + ("%0.16X" % q).decode('hex')
  return md5.new(md5.new(m).hexdigest().upper() + v.upper()).hexdigest().upper()

def runCommand(cmd, msgId):
  global ClientID, PSessionID, http, Referer
  ret = 'Run Command: [{0}]\n'.format(cmd)
  try:
    popen_obj = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    (stdout, stderr) = popen_obj.communicate()

    ret += stdout.strip()
    ret += '\n' + stderr.strip()
  except Exception, e:
    ret += e
  ret = ret.replace('\\', '\\\\\\\\').replace('\t', '\\\\t').replace('\r', '\\\\r').replace('\n', '\\\\n')
  ret = ret.replace('"', '\\\\\\"')
  http.Post("http://d.web2.qq.com/channel/send_buddy_msg2", (
    ('r', '{{"to":{0},"face":522,"content":"[\\"{4}\\",[\\"font\\",{{\\"name\\":\\"Arial\\",\\"size\\":\\"10\\",\\"style\\":[0,0,0],\\"color\\":\\"000000\\"}}]]","msg_id":{1},"clientid":"{2}","psessionid":"{3}"}}'.format(msg['value']['from_uin'], msgId, ClientID, PSessionID, ret)),
    ('clientid', ClientID),
    ('psessionid', PSessionID)
  ), Referer)


logging.basicConfig(filename='qq.log', level=logging.DEBUG, format='%(asctime)s  %(filename)s[line:%(lineno)d] %(levelname)s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S')


http = HttpClient()


initUrl = "https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&target=self&style=5&mibao_css=m_webqq&appid={0}&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb2.qq.com%2Floginproxy.html&f_url=loginerroralert&strong_login=1&login_state=10&t=".format(APPID)

html = http.Get(initUrl)

sign = re.search(r'var g_login_sig=encodeURIComponent\("(.+?)"\);', html)

if sign is None:
  logging.error('get login sign error')
else:
  sign = sign.group(1)

logging.info('get sign : %s', sign)



html = http.Get("https://ssl.ptlogin2.qq.com/check?uin={0}&appid={1}&js_ver=10038&js_type=0&login_sig={2}&u1=http%3A%2F%2Fweb2.qq.com%2Floginproxy.html&r=0.5331138293443659".format(QQ, APPID, sign))

html = html.split("'")

logging.debug(html)

if len(html) == 0:
  exit()

vc = None

if html[1] == '1':
  logging.info('need validate code')
  http.Download("https://ssl.captcha.qq.com/getimage?aid={0}&r={1}&uin={2}".format(APPID, random.random(), QQ), "v.jpg")
  i = 0
  VF = '{0}/v.txt'.format(os.getcwd())
  while i < 20:
    if os.path.exists(VF):
      vc = file(VF, 'r').read()
      os.remove(VF)
      break
    i += 1
    time.sleep(3)
else:
  vc = html[3]

if vc is None:
  logging.error('get validate code error')
  quit()

vc = vc.strip()

logging.info(vc)

html = http.Get("https://ssl.ptlogin2.qq.com/login?u={0}&p={1}&verifycode={2}&webqq_type=10&remember_uin=1&login2qq=1&aid={3}&u1={4}&h=1&ptredirect=0&ptlang=2052&daid=164&from_ui=1&pttype=1&dumy=&fp=loginerroralert&action=1-41-15424&mibao_css=m_webqq&t=1&g=1&js_type=0&js_ver=10038&login_sig={5}".format(QQ, getEncPass(QQ, PASS, vc), vc, APPID, "http%3A%2F%2Fweb.qq.com%2Floginproxy.html%3Flogin2qq%3D1%26webqq_type%3D10", sign), "https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164")

html = html.split("'")

if html[1] != '0':
  logging.error(html)
  quit()

PTWebQQ = http.getCookie('ptwebqq')

logging.info('PTWebQQ: {0}'.format(PTWebQQ))

html = http.Get(html[5])

while 1:
  html = http.Post('http://d.web2.qq.com/channel/login2', (
    ('r', '{{"status":"online","ptwebqq":"{0}","passwd_sig":"","clientid":"{1}","psessionid":"{2}"}}'.format(PTWebQQ, ClientID, PSessionID)),
    ('clientid', ClientID),
    ('psessionid', 'null')
  ), 'http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3')

  logging.debug(html)

  ret = json.loads(html)

  if ret['retcode'] != 0:
    quit()

  VFWebQQ = ret['result']['vfwebqq']
  PSessionID = ret['result']['psessionid']

  logging.info('Login success')

  Referer = 'http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=2'
  MsgID = 38200000

  E = 0
  while 1:
    html = http.Post('http://d.web2.qq.com/channel/poll2', (
      ('r', '{{"clientid":"{0}","psessionid":"{1}","key":0,"ids":[]}}'.format(ClientID, PSessionID)),
      ('clientid', ClientID),
      ('psessionid', PSessionID)
    ), Referer)

    try:
      ret = json.loads(html)
    except Exception, e:
      logging.debug(e)
      E += 1
      if E > 3:
        break
      time.sleep(2)
      continue

    E = 0

    if ret['retcode'] == 102:#无消息
      continue
    if ret['retcode'] == 116:#更新PTWebQQ值
      PTWebQQ = ret['p']
      continue
    if ret['retcode'] == 0:
      for msg in ret['result']:
        msgType = msg['poll_type']
        if msgType == 'message':#QQ消息
          txt = msg['value']['content'][1]
          logging.debug(txt)
          if txt[0] == '#':
              thread.start_new_thread(runCommand, (txt[1:].strip(), MsgID))
              MsgID += 1
          if txt[0:4] == 'exit':
              http.Get('http://d.web2.qq.com/channel/logout2?ids=&clientid={0}&psessionid={1}'.format(ClientID, PSessionID), Referer)
              exit()
        elif msgType == 'kick_message':
          logging.error(msg['value']['reason'])
          exit()
        elif msgType != 'input_notify':
          logging.debug(msg)
    else:
      logging.debug(ret)

# vim: tabstop=2 softtabstop=2 shiftwidth=2 expandtab
