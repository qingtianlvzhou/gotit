#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import logging

import web
from web.contrib.template import render_jinja
import requests

from addons import get_old_cet, get_book
from addons.get_CET import CET
from addons.zfr import ZF, Login
from addons.autocache import memorize
from addons import config
from addons.config import (index_cache, debug_mode, zheng_alert)
from addons.RedisStore import RedisStore
from addons.utils import (init_redis, get_score_jidi, 
        collect_checkcode, init_mongo, get_last_one_by_date)
from addons import errors


#import apis
import manage
from forms import cet_form, xh_form, login_form

# debug mode
web.config.debug = debug_mode

urls = (
    '/', 'index',
    '/zheng', 'zheng',
    '/more/(.+)', 'more',
    '/score', 'score',
    '/cet', 'cet',
    '/cet/old', 'cet_old',
    '/libr', 'libr',
    #'/api', apis.apis,
    '/manage', manage.manage,
    '/contact.html', 'contact',
    '/notice.html', 'notice',
    '/help/gpa.html', 'help_gpa',
    '/comment.html', 'comment',
    '/donate.html', 'donate',
)

# main app
app = web.application(urls, globals(),autoreload=False)


# session
if web.config.get('_session') is None:
    session = web.session.Session(app, RedisStore(), {'count': 0, 'xh':False})
    web.config._session = session
else:
    session = web.config._session

# render templates
render = render_jinja('templates', encoding='utf-8',globals={'context':session})

#logger = init_log('code.py')

# init mongoDB
mongo = init_mongo()

# 首页索引页
class index:

    def GET(self):
        _alert=mongo.zheng.find_one()
        return render.index(alert=_alert)


# 成绩查询
class zheng:

    def GET(self):

        try:
            zf = ZF()
            time_md5 = zf.pre_login()
        except errors.ZfError, e:
            return render.serv_err(err=e.value)
        session['time_md5'] = time_md5
        # get checkcode
        r = init_redis()
        checkcode = r.hget(time_md5, 'checkcode')
        _alert=mongo.zheng.find_one()
        return render.zheng(alert=_alert, checkcode=checkcode)

    def POST(self):
        try:
            content = web.input()
        except UnicodeDecodeError:
            content = web.input()
            logging.error('UnicodeDecodeError '+str(content))
        try:
            session['xh'] = content['xh']
            t = content['type']
            time_md5 = session['time_md5']
            collect_checkcode(content.get('verify', ''))
        except (AttributeError, KeyError), e:
            logging.error(str(content))
            return render.alert_err(error='请检查您是否禁用cookie', url='/zheng')

        try:
            zf = Login()
            zf.login(time_md5, content)
            __dic = {
                    '1': zf.get_score,
                    '2': zf.get_kaoshi,
                    '3': zf.get_kebiao,
                    '4': zf.get_last_kebiao,
                    }
            if t not in __dic.keys():
                return render.alert_err(error='输入不合理', url='/zheng')
            return render.result(table=__dic[t]())
        except errors.PageError, e:
            return render.alert_err(error=e.value, url='/zheng')

class more:
    """连续查询 二次查询
    """
    def GET(self, t):
        if session['xh'] is False:
            raise web.seeother('/zheng')
        try:
            __dic1 = { # need xh
                    'oldcet':get_old_cet,
                    }
            if t in __dic1.keys():
                return render.result(table=__dic1[t](session['xh']))

            elif t=='score':
                try:
                    score, jidi=get_score_jidi(session['xh'])
                except errors.PageError, e:
                    return render.alert_err(error=e.value, url='/score')
                return render.result(table=score, jidian=jidi)

            zf = Login()
            __dic = { # just call
                    'zheng': zf.get_score,
                    'kaoshi': zf.get_kaoshi,
                    'kebiao': zf.get_kebiao,
                    'lastkebiao': zf.get_last_kebiao,
                    }
            if t in __dic.keys():
                zf.init_after_login(session['time_md5'], session['xh'])
                return render.result(table=__dic[t]())
            raise web.notfound()
        except (AttributeError, TypeError, KeyError, requests.TooManyRedirects):
            raise web.seeother('/zheng')
	except errors.RequestError, e:
	    return render.serv_err(err=e)

# cet

class cet:

    @memorize(index_cache)
    def GET(self):
        form = cet_form()
        if config.baefetch:
            return render.cet_bae(form=form)
        else:
            return render.cet(form=form)
        # return render.cet_raise()

    def POST(self):
        form = cet_form()
        if not form.validates():
            return render.cet(form=form)
        else:
            zkzh = form.d.zkzh
            name = form.d.name
            name = name.encode('utf-8')
            items = ["学校","姓名","阅读", "写作", "综合",
                    "准考证号", "考试时间", "总分", "考试类别",
                    "听力"]
            cet = CET()
            res = cet.get_last_cet_score(zkzh, name)
            return render.result_dic(items=items, res=res)


class cet_old:
    """
    往年cet成绩查询
    """
    @memorize(index_cache)
    def GET(self):
        form=xh_form
        title='往年四六级成绩'
        return render.normal_form(title=title, form=form)
    def POST(self):
        form = xh_form()
        title='往年四六级成绩'
        if not form.validates():
            return render.normal_form(title=title, form=form)
        else:
            xh = form.d.xh
            session['xh']=xh
        try:
            table=get_old_cet(xh)
            return render.result(table=table)
        except errors.RequestError, e:
            return render.serv_err(err=e)


class libr:
    """
    图书馆相关
    """
    @memorize(index_cache)
    def GET(self):
        form=login_form
        title='图书馆借书查询'
        return render.normal_form(title=title, form=form)

    def POST(self):
        form=login_form()
        title='图书馆借书查询'
        if not form.validates():
            return render.normal_form(title=title,form=form)
        else:
            xh, pw=form.d.xh, form.d.pw
            session['xh']=xh
        try:
            table=get_book(xh,pw)
        except errors.PageError, e:
            return render.alert_err(error=e.value, url='/libr')
        return render.result(table=table)


# 全部成绩
class score:

    def GET(self):
        form = xh_form()
        alert=mongo.score.find_one()
        return render.score(form=form, alert=alert)

    def POST(self):
        form = xh_form()
        if not form.validates():
            return render.score(form=form)
        else:
            xh = form.d.xh
            session['xh']=xh
            try:
                score, jidi=get_score_jidi(xh)
            except errors.PageError, e:
                return render.alert_err(error=e.value)
            except errors.RequestError, e:
                return render.serv_err(err=e)

            return render.result(table=score, jidian=jidi)

            # else:
            #    return "成绩查询源出错,请稍后再试!"

# 平均学分绩点计算说明页面


class help_gpa:

    @memorize(index_cache)
    def GET(self):
        return render.help_gpa()

# 评论页面, 使用多说评论

class comment:

    def GET(self):
        return render.comment()


class contact:

    """contact us page"""
    @memorize(index_cache)
    def GET(self):
        return render.contact()

# notice

class notice:

    def GET(self):
        news = mongo.notice.find().sort("datetime",-1)
        return render.notice(news=news)


# 赞助页面

class donate:

    def GET(self):
        sponsor = mongo.donate.find().sort("much",-1)
        return render.donate(sponsor=sponsor)


# web server
def session_hook():
    """ share session with sub apps
    """
    web.ctx.session = session

def notfound():
    """404
    """
    return web.notfound(render.notfound())

def internalerror():
    """500
    """
    web.setcookie('webpy_session_id','',-1)
    return web.internalerror(render.internalerror())

app.notfound = notfound
app.internalerror = internalerror
app.add_processor(web.loadhook(session_hook))

# for gunicorn
application = app.wsgifunc()
