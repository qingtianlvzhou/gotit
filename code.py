#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')


import web
from web import form
from web.contrib.template import render_jinja

# addons
from addons.calc_GPA import GPA
from addons.get_CET import CET
from addons.zf import ZF#, get_json
from addons.get_all_score import ALL_SCORE
from addons.autocache import memorize
from addons import config
from addons.config import index_cache, debug_mode, sponsor, zheng_alert
web.config.debug = debug_mode

import apis


urls = (
    '/', 'index',
    '/zheng', 'zheng',
    '/score', 'score',
    '/cet', 'cet',
    '/api', apis.apis,
    '/contact.html', 'contact',
    '/notice.html', 'notice',
    '/help/gpa.html', 'help_gpa',
    '/comment.html', 'comment',
    '/donate.html', 'donate',
    '/root.txt', 'ttest',
    '/status', 'status',
)

# render = web.template.render('./template/') # your templates
render = render_jinja('templates', encoding='utf-8')
all_client = {}

# forms
# def get_form(viewstate):
#    info_form = form.Form(
#        form.Textbox("number", description="学号:",class_="span3",pre="&nbsp;&nbsp;"),
#        form.Password("password", description="密码:",class_="span3",pre="&nbsp;&nbsp;"),
#        form.Textbox("verify", description="验证码:",class_="span3",pre="&nbsp;&nbsp;"),
#        form.Dropdown('Type',[('3', '本学期课表查询'),('1', '本学期成绩查询'), ('2', '考试时间查询'),('4', '平均学分绩点查询')],description="查询类型:",pre="&nbsp;&nbsp;"),
#        form.Hidden('viewstate',value=viewstate),
#        validators = [
#            form.Validator('输入不合理!', lambda i:int(i.number) > 9)]
#        )
#    return info_form()

cet_form = form.Form(
    form.Textbox(
        "zkzh",
        description="准考证号:",
        class_="span3",
        pre="&nbsp;&nbsp;"),
    form.Textbox(
        "name",
        description="姓名:",
        class_="span3",
        pre="&nbsp;&nbsp;"),
    validators=[
        form.Validator('输入不合理!', lambda i:int(i.zkzh) != 15)]
)
xh_form = form.Form(
    form.Textbox(
        "xh",
        description="学号:",
        class_="span3",
        pre="&nbsp;&nbsp;")
)


def get_index_form(time_md5):
    index_form = '\
            <table><tr><th><label for="xh">学号:</label></th><td>&nbsp;&nbsp;<input type="text" id="xh" name="xh" class="span3"/></td></tr>\
            <tr><th><label for="pw">密码:</label></th><td>&nbsp;&nbsp;<input type="password" id="pw" name="pw" class="span3"/></td></tr>\
            <tr><th><label for="number">验证码:</label></th>\
            <td>&nbsp;&nbsp;<span><input type="text" id="verify" name="verify"/></span>&nbsp;<span><img style="position:absolute;" src="/static/pic/%s.gif" alt="" height="35" width="92"/></span></td>\
                <td></td>\
                </tr>\
            <tr><th><tr><th><label for="Type">查询类型:</label></th><td>&nbsp;&nbsp;<select id="type" name="type">\
                <option value="1">成绩查询</option>\
                <option value="2">考试时间查询</option>\
                <option value="3">课表查询</option></select></td></tr>\
            <input type="hidden" value="%s" name="time_md5"/></table>' % (time_md5, time_md5)
    return index_form

# 首页索引页


class index:

    @memorize(index_cache)
    def GET(self):
        return render.index(alert=zheng_alert)


# 成绩查询
class zheng:

    def GET(self):
        zf = ZF()
        viewstate, time_md5 = zf.pre_login()
        all_client[time_md5] = (zf, viewstate)
        form = get_index_form(time_md5)
        return render.zheng(alert=zheng_alert, form=form)

    def POST(self):
        content = web.input()
        self.xh = content['xh']
        self.pw = content['pw']
        t = content['type']
        yanzhengma = content['verify']
        time_md5 = content['time_md5']

        try:
            value = all_client.pop(time_md5)
            zf = value[0]
            viewstate = value[1]
        except KeyError:
            return render.key_error()

        zf.set_user_info(self.xh, self.pw)
        ret = zf.login(yanzhengma, viewstate)
        if ret.find('欢迎您') != -1:
            pass
        elif ret.find('密码错误') != -1:
            return render.pw_error()

        elif ret.find('验证码不正确') != -1:
            return render.recg_error()
        else:
            return render.ufo_error()

        if t == "1":
            table = zf.get_score()
        elif t == "2":
            table = zf.get_kaoshi()
        elif t == "3":
            table = zf.get_kebiao()
        else:
            return render.input_error()
        if table:
            error = None
            return render.result(table=table, error=error)
        else:
            table = None
            error = "can not find your index table"
            return render.result(table=table, error=error)

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
            items = [
                "学校",
                "姓名",
                "阅读",
                "写作",
                "综合",
                "准考证号",
                "考试时间",
                "总分",
                "考试类别",
                "听力"]
            cet = CET()
            res = cet.get_last_cet_score(zkzh, name)
            # s = ""
            # for i in res.keys():
            #    s = "%s%s\n%s\n"%(s,i,res[i])
            # return s
            return render.result_dic(items=items, res=res)

# contact us

class status:

    def GET(self):
        return len(all_client.keys())


class contact:

    """contact us page"""
    @memorize(index_cache)
    def GET(self):
        return render.contact()

# notice


class notice:

    @memorize(index_cache)
    def GET(self):
        return render.notice()


# 全部成绩
class score:

    @memorize(index_cache)
    def GET(self):
        form = xh_form()
        return render.score(form=form)

    def POST(self):
        form = xh_form()
        if not form.validates():
            return render.score(form=form)
        else:
            xh = form.d.xh
            a = ALL_SCORE()
            table = a.get_all_score(xh)
            gpa = GPA(xh)
            gpa.getscore_page()
            # table = gpa.get_all_score()
            jidian = gpa.get_gpa()["ave_score"]

            if table:
                return render.result(table=table, jidian=jidian)
            else:
                table = None
                error = "can not get your score"
            return render.result(table=table, error=error)
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

# 赞助页面


class donate:

    def GET(self):
        return render.donate(sponsor=sponsor)

# 阿里妈妈认证


class ttest:

    def GET(self):
        return render.root()


# for gunicorn
application = web.application(urls, globals(), autoreload=False).wsgifunc()

# just for test
app = web.application(urls, globals(),autoreload=False)
