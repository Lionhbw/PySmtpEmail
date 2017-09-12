'''
Created on 2017年9月11日

@author: 黄柏文

Contact me:hackerhuang@qq.com
'''

import smtplib
import email.utils
import email.header
import email.mime.text
import email.mime.multipart
import email.mime.base
import mimetypes
import logging

logging.basicConfig(level = logging.INFO)

class EnvelopeInfo(object):
    '''
    这个类就相当于信封头
    '''
    def __init__(self,strFromWho,toWhoListStr):
        '''
        strFromWho 必须是 登录邮箱的账户名，也就是说，发送者和登录邮箱者必须是同一个
        字符串，否则，极容易被当作垃圾邮件被邮箱提供商BAN掉
        对于strFromWho和toWhoListStr来说，尽管前者是字符串，后者是字符串数组或
        单个字符串，但是每个字符串应该是  称呼 <实际邮件地址@邮箱提供商>  这样的格式，
        比如：
                圣祖师爷马云<alibabajack@aliyun.com>
        如果没有称呼，也需要用尖括号把邮箱地址括起来：
                <alibabajack@aliyun.com>
        后者是字符串数组，如果多个收件人，则：
                ['<mahuateng@qq.com>','圣祖师爷马云<alibabajack@aliyun.com>']
        后者如果是单个字符串的话，则多个收件人之间，逗号也必须要包括在里面：
                '<mahuateng@qq.com>,圣祖师爷马云<alibabajack@aliyun.com>'
        '''
        # 用于邮箱标记，美观显示，用户体验好，下面的toWhoListStr也是这样的
        self._originFromWho = strFromWho
        # 用于邮箱底层标记，不作实际发送用途
        self._fromWho = self._InsideHandle(strFromWho)
        # 用于实际发送，底层操作
        self._fromWhoRow = self._GetRowInfo(strFromWho)[1]
        
        self._toWhoRowList = []
        
        # 分割联系人
        targetList = []
        
        if isinstance(toWhoListStr, str):
            targetList = toWhoListStr.split(',')
        if len(targetList) > 0 or isinstance(toWhoListStr, list):
            if not len(targetList) > 0:
                targetList = toWhoListStr
            handleList = []
            for eachobj in targetList:
                # 去掉左右空格
                eachobj = eachobj.strip()
                handleList.append(self._InsideHandle(eachobj))
                self._toWhoRowList.append(self._GetRowInfo(eachobj)[1])
            # 得到最终处理结果
            self._toWhoList = ','.join(handleList)
            # 重新修正为原始数据
            self._originToWhoList = ','.join(targetList)
        else:
            raise ValueError('参数二不合法')
    
    def GetToWhoList(self):
        '''
        一般用于MIME类的['To']成员，除此外，不应该使用
        '''
        return self._toWhoList
    
    def GetRowToWhoList(self):
        '''
        一般用于SMTP服务器的sendmail函数，除此外，不应该使用
        '''
        return self._toWhoRowList
    
    def _GetOriginToWhoList(self):
        '''
        一般用于美化展示备份，客户任何时候都不应该调用
        '''
        return self._originToWhoList
    
    def GetFromWho(self):
        '''
        一般用于MIME类的['From']成员，除此外，不应该使用
        '''
        return self._fromWho
    
    def GetRowFromWho(self):
        '''
        一般用于SMTP服务器的sendmail函数，除此外，不应该使用
        '''
        return self._fromWhoRow
    
    def _GetOriginFromWho(self):
        '''
        一般用于美化展示备份，客户任何时候都不应该调用
        '''
        return self._originFromWho
    
    def _GetRowInfo(self,strInfo):
        '''
        将客户的输入转化为内部可用的数据
        '''
        return email.utils.parseaddr(strInfo)
    
    def _InsideHandle(self,strInfo):
        '''
        将信息转化为utf-8存储起来
        '''
        nickname, mailAddr = self._GetRowInfo(strInfo)
        return email.utils.formataddr((email.header.Header(nickname,'utf-8').encode(), mailAddr))

class EmailContent(object):
    def __init__(self,envelopeObj,strEmailTitle,strEmailContent='',strContentType = 'plain'):
        '''
        这是实际邮件内容类。注意，每个邮件都应该有一个对应的EnvelopeInfo对象作为初始化参数，
        EnvelopeInfo对象是作为这封邮件最终发送的设置，表明这封邮件从哪里发送到哪里的，所以
        应该先实例化好EnvelopeInfo类对象，再实例化本类对象。
        实例化对象的时候，至少传入EnvelopeInfo对象以及邮件的标题
        邮件的内容默认是空字符串，以及类型默认是plain，主要是为了后续能够增加附件
         如果是附带了附件，建议设置为 html，否则内容中引用附件的html代码可能不能正确显示
        '''
        if not isinstance(envelopeObj, EnvelopeInfo):
            raise TypeError('附件必须包含一个原有的EnvelopeInfo作为基本发送设置')
        self._envelope = envelopeObj
        self._title = strEmailTitle
        self.SetContent(strEmailContent)
        self._contentType = strContentType
        self._msg = email.mime.multipart.MIMEMultipart('alternative')
        self._attachDict = {}
    
    def SetContent(self,strContent):
        '''
        strContent：字符串类型。重新设置发送的邮件内容
        '''
        self._content = strContent
    
    def SetContentType(self,strContentType):
        '''
        strContent：字符串类型。重新设置发送的邮件内容类型，如plain或者html，注意
        如果是附带了附件，建议设置为 html，否则内容中引用附件的html代码可能不能正确显示
        '''
        self._contentType = strContentType
    
    def AddAttachment(self,strRefKey,strAttachLocalPath):
        '''
        strRefKey：字符串类型。唯一标识附件的ID，在html代码中引用的时候加上 cid:strRefKey ，比如
        如果增加了一个图片附件 ，strRefKey为  MyPic，那么引用的时候代码为：
                <img src = "cid:MyPic"/>
        strAttachLocalPath：字符串类型。附件在本地电脑的路径。
        '''
        self._attachDict[strRefKey] = strAttachLocalPath
    
    def RemoveAttachmentByKey(self,strRefKey):
        '''
        strRefKey：字符串类型。唯一标识附件的ID，通过strRefKey移除特定附件
        '''
        if strRefKey in self._attachDict:
            del self._attachDict[strRefKey]
    
    def GetEnvelope(self):
        '''
        由外部类调用，获取要发送的最终目的地址
        '''
        return self._envelope
    
    def GetFinalSendingData(self):
        '''
        获取最终要发送的底层数据内容
        '''
        if len(self._attachDict) > 0 and self._contentType == 'plain':
            logging.info('有附件，但是内容类型为plain，不解析html可能会出现非想要的效果')
        
        # 兼容不能浏览html代码的客户端
        self._msg.attach(email.mime.text.MIMEText(self._content,'plain','utf-8'))
        self._msg.attach(email.mime.text.MIMEText(self._content,self._contentType,'utf-8'))
        
        self._msg['From'] = self._envelope.GetFromWho()
        self._msg['To'] = self._envelope.GetToWhoList()
        self._msg['Subject'] = email.header.Header(self._title,'utf-8').encode()
        
        # 遍历处理附件
        for eachAttachKey,eachAttachPath in self._attachDict.items():
            with open(eachAttachPath,'rb') as f:
                mimeType,mimeEncoding = mimetypes.guess_type(eachAttachPath)
                if mimeEncoding or (mimeType is None):
                    mimeType = "application/octet-stream"
                guessMainType,guessSubType = mimeType.split("/")
                mimeInfo = email.mime.base.MIMEBase(guessMainType,guessSubType,filename = eachAttachPath)
                mimeInfo.add_header('Content-Disposition', 'attachment',filename = eachAttachPath)
                mimeInfo.add_header('Content-ID','<%s>' % eachAttachKey)
                mimeInfo.add_header('X-Attachment-Id', '<%s>' % eachAttachKey)
                mimeInfo.set_payload(f.read())
                email.encoders.encode_base64(mimeInfo)
                self._msg.attach(mimeInfo)
        return self._msg.as_string()

class MailCarrier(object):
    def __init__(self):
        '''
        邮箱投递员类。模拟发送邮件
        '''
        self._srv = None
        
    def ReachOffice(self,strSmtpAddr,intSmtpPort,strUsername,strPassword,debugView = True):
        '''
        strSmtpAddr：字符串类型。SMTP服务器地址
        intSmtpPort：整数类型。SMTP服务器端口
        strUsername：登录用户名
        strPassword：登录密码
        debugView：是否开启调试输出
        普通登录
        '''
        self._srv = smtplib.SMTP(strSmtpAddr,intSmtpPort)
        self._Login(strUsername, strPassword,debugView)
    
    def ReachOfficeTLS(self,strSmtpAddr,intSmtpPort,strUsername,strPassword,debugView = True):
        '''
        使用正常的端口25，并用tls加密
        '''
        self._srv = smtplib.SMTP(strSmtpAddr,intSmtpPort)
        self._srv.starttls()
        self._Login(strUsername, strPassword,debugView)
    
    def ReachOfficeSSL(self,strSmtpAddr,intSmtpPort,strUsername,strPassword,debugView = True):
        '''
        使用SSL
        '''
        self._srv = smtplib.SMTP_SSL(strSmtpAddr,intSmtpPort)
        self._Login(strUsername, strPassword,debugView)
    
    def _Login(self,strUsername,strPassword,debugView):
        '''
        内部使用接口
        '''
        self._srv.login(strUsername, strPassword)
        self._srv.set_debuglevel(debugView)
    
    def PostMail(self,emailObj):
        '''
        发送邮件
        '''
        if not isinstance(emailObj, EmailContent):
            raise TypeError('必须是EmailContent对象实例')
        emailEnvelop = emailObj.GetEnvelope()
        self._srv.sendmail(emailEnvelop.GetRowFromWho(),emailEnvelop.GetRowToWhoList(),emailObj.GetFinalSendingData())
    
    def FinishedPost(self):
        '''
        退出登录
        '''
        self._srv.quit()

if __name__ == '__main__':
    # 接收的所有人，多个收件人用逗号，没有昵称可以不写，但是邮件地址一定要带上尖括号包围
    recvTarget = '圣祖师爷马云<alibabajackma@aliyun.com>,小马哥马化腾<mht@qq.com>'
    sender = '趴在窗户上的苍蝇<YourEmailAddress@YourMTA.com>'
    # 构造信封包
    en = EnvelopeInfo(sender,recvTarget)
    # 构造邮件内容
    letter = EmailContent(en,'This is The Title')
    # 因为插入了附件，所以这里重新设置内容
    # 当然，也可以在上面的构造函数中，直接就把内容写好
    letter.SetContent('这是内容<img src="cid:x"/><br/>这是普通的另外一行内容')
    # 这里可以设置类型，如果有图片附件要引用的话，建议改为 html
    letter.SetContentType('html')
    # 注意这里的key，用在了上面的邮件内容中用来引用的 cid:key
    letter.AddAttachment('x', r"d:\attachmentTest.png")
    # 构造一个邮递员
    postman = MailCarrier()
    # 到达邮局（登录邮箱），如果是25端口支持SSL，可以用starttls那个函数，如果是原生SSL，用另外一个登陆
    # 比如，测试发现网易和腾讯普通邮用普通的25，其中，网易应该是支持TLS的
    # 腾讯企业邮箱只能用SSL登陆
    postman.ReachOffice('smtp.126.com', 25, 'example@126.com', 'YourPasswordHere')
    x = input('登录完毕，任意键继续') # 这行可以去掉
    # 发送邮件，注意，这里发送的是邮件内容，因为信封包到时候，会在投递类中自动处理
    postman.PostMail(letter)
    x = input('发送搞定，任意键继续') # 这行可以去掉
    # 退出登录
    postman.FinishedPost()
