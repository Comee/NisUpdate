'''
Created on 2014年12月7日

@author: Leo
'''
import tkinter as tk
import random, time
from tkinter import filedialog 
from tkinter import messagebox 
from pubsub import pub
from threading import Thread
import logging.handlers
import os, sys
import zipfile, shutil
from bs4 import BeautifulSoup, SoupStrainer
import configparser, ast
import ntpath
from operator import itemgetter
import filecmp

bitmaps = ["error", "gray75", "gray50", "gray25", "gray12", "hourglass", "info", "questhead", "question", "warning"]

# 字符长度数组
widths = [
    (126, 1), (159, 0), (687, 1), (710, 0), (711, 1),
    (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
    (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1),
    (8426, 0), (9000, 1), (9002, 2), (11021, 1), (12350, 2),
    (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1),
    (55203, 2), (63743, 1), (64106, 2), (65039, 1), (65059, 0),
    (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
    (120831, 1), (262141, 2), (1114109, 1)]
    


#----------------------------------------------------------------------         
# 居中window        
def center_window(self, w=400, h=400, title="Comee"):
    self.title(title)
    self.resizable(False, False)

    # get screen width and height
    ws = self.winfo_screenwidth()
    hs = self.winfo_screenheight()
    # calculate position x, y
    x = (ws / 2) - (w / 2)
    y = (hs / 2) - (h / 2)
    
    # width x height + x_offset + y_offset:
    self.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    
#----------------------------------------------------------------------
# 创建Bitmap    
def createBitmap(root):
    canvas_width = 300
    canvas_height = 80

    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height)
    canvas.pack()

    
    nsteps = len(bitmaps)
    step_x = int(canvas_width / nsteps)

    for i in range(0, nsteps):
        canvas.create_bitmap((i + 1) * step_x - step_x / 2, 20, bitmap=bitmaps[i])
        
        
#----------------------------------------------------------------------   
'''
description:获得字符串长度，一个中文字符算2
'''          
def get_str_width(s):
    slen = 0
    for word in s:
        slen += get_width(ord(word))
    return slen


#----------------------------------------------------------------------
'''
description:从字符串尾部获取指定宽度的字符串，一个中文字符串算2
return: 返回截取后的字符串
'''
def get_sub_str(spath, width):
    s = spath
    s0 = s[::-1]
    slen = 0
    for i in range(len(s0)):
        slen += get_width(ord(s0[i]))
        if slen > width:
            return s[:3] + 3 * "." + s[len(s) - i:]
    return s

#----------------------------------------------------------------------          
def get_width(o):
        """Return the screen column width for unicode ordinal o."""
        if o == 0xe or o == 0xf:
            return 0
        for num, wid in widths:
            if o <= num:
                return wid
        return 1   

#---------------------------------------------------------------------- 
'''
description: 判断是否是空目录，若目录不存在，则返回True
'''
def is_empty_dir(directory):
    return sum([len(files) + len(dirs) for root, dirs, files in os.walk(directory)]) == 0    
    
#----------------------------------------------------------------------     
'''
description:遍历目录，包含文件和空目录
return  list [[path,isfile,isleft,isright,issamefile],...]
'''
def walk_list(leftdir, rightdir):
    alllist = []
    for root, dirs, files in os.walk(leftdir):
        for file in files: 
            filelist = [os.path.join(root, file).replace(leftdir, ""), True, True, False, False]            
            alllist.append(filelist)
        for directory in dirs:
            if is_empty_dir(os.path.join(root, directory)):
                directorylist = [os.path.join(root, directory).replace(leftdir, ""), False, True, False, False] 
                alllist.append(directorylist)
    
    
    cmplist = [itemgetter(0, 1)(i) for i in alllist]
    for root, dirs, files in os.walk(rightdir):
        for file in files:  
            # asbpath,isFile,isOld,isNew  
            filelist = [os.path.join(root, file).replace(rightdir, ""), True, False, True, False]
            cmpfilelist = filelist[:2]  
            if cmplist.count(tuple(cmpfilelist)) > 0:
                i = cmplist.index(tuple(cmpfilelist))
                alllist[i][3] = True
                if filecmp.cmp(leftdir + alllist[i][0], rightdir + alllist[i][0]):
                    alllist[i][4] = True
            else:
                alllist.append(filelist)    
                        
        for directory in dirs:
            if is_empty_dir(os.path.join(root, directory)):
                directorylist = [os.path.join(root, directory).replace(rightdir, ""), False, False, True, False] 
                cmpdirectorylist = directorylist[0:2] 
                if cmplist.count(tuple(cmpdirectorylist)) > 0:
                    i = cmplist.index(tuple(cmpdirectorylist))
                    alllist[i][3] = True
                else:
                    alllist.append(directorylist)
    return alllist
             
#----------------------------------------------------------------------
class LogFrame(tk.Toplevel):
    """显示日志"""
  
    #----------------------------------------------------------------------
    def __init__(self, index=None, oldpath="", newpath="", logger=None):
        """Constructor"""
        
        # 格式化日期  yyyy-mm-dd hh24:mi:ss
        self.ISOTIMEFORMAT = '%Y-%m-%d %X'
        
        # nis path
        self.oldpath = oldpath
        self.newpath = newpath
        
        # 直接完全替换
        self.replace_all = False
        
        # 排除操作目录  针对所有操作
        self.exclusion_dirs = ["WEB-INF\orcus\grab", "WEB-INF\dlls", "WEB-INF\rep-files"]
        self.exclusion_files = ["WEB-INF\orcus\diagnosis.xml"]
        
        # 排除的待合并的文件
        self.merge_xml_files = ["WEB-INF\orcus_web.xml", "WEB-INF\orcus\diagnosis.xml"]
        
        # 必须要进行先删除，后拷贝操作的目录
        self.force_delete_update_directory = ["pages", "WEB-INF\classes"]
        
        # 排除的key 值不是true或false的都属于被排除的
        self.exclusion_element_keys = ["localhost", "web.context.url", "server.path", "Course.Parse.loader", "Course.Parse.loader.ftp.url", "Course.Parse.loader.dsName", "Course.Parse.loader.ws.address"]  # 不覆盖的element元素
        # 针对上一项目的补充，如值不是true或false 但是需要进行更新， 例如App.Version
        self.must_update_element_keys = ["App.Version"]
        # 与上2项结合使用：开关选项 orcusweb.xml中element元素值是true或false的元素是需要更新的，其他的element元素是不需要更新的；若为true，则其他的element元素也更新
        self.VALUE_TRUE_FALSE_PROTECTED = False
        
        self.BO_DELETE_ELEMENT = True
        self.OC_UPDATE_ELEMENT = True
        self.BO_DELETE_TASK = True
        self.OC_UPDATE_TASK = True
        self.BO_DELETE_FILE = True
        self.BO_DELETE_EMPTY_DIR = True
        
        
        self.logger = logger
        self.initconfig()
        
        
        
        # 过滤exclusion_files
        self.exclusion_merge()  # 必须在initconfig之后
        
        
        tk.Toplevel.__init__(self)
        center_window(self, w=750, h=500, title="日  志")
  
        # 处理x 关闭窗口事件，用于覆盖原事件
        self.protocol("WM_DELETE_WINDOW", self.onClose)
        
        S = tk.Scrollbar(self)
        T = tk.Text(self, height=500, width=500)
        S.pack(side=tk.RIGHT, fill=tk.Y)
        T.pack(side=tk.LEFT, fill=tk.Y)
        S.config(command=T.yview)
        T.config(yscrollcommand=S.set)
        
        T.tag_configure('big', foreground='#476042', font=('黑体', 20, 'bold'))
        T.tag_configure("center", justify='center')
        T.tag_configure('big_center', justify='center', foreground='#476042', font=('黑体', 20, 'bold'))
        T.tag_configure('color_info', foreground='#476042', font=('宋体', 12))
        T.tag_configure('color_error', foreground='red', font=('宋体', 12, 'bold'))
        T.tag_configure('color_important', foreground='green', font=('宋体', 12, 'bold'))
        
        # 防止编辑Text
        T.bind("<KeyPress>", lambda e : "break")
        
        self.T = T
        
        # 根据index调用事件
        self.onIndex(index)
        
  
    #----------------------------------------------------------------------
    '''
    description:根据index来处里事件
    '''
    def onIndex(self, index):
        if index == 2:
            self.T.insert(tk.END, "\n更新记录\n\n", "big_center")
            self.info("原始nis目录为：%s" % self.oldpath)
            self.info("新nis目录为：%s" % self.newpath)
            
            t1 = Thread(target=self.update_nis)  # 指定目标函数，传入参数，这里参数也是元组  
            t1.start()  # 启动线程  
            
        elif index == 3:
            print("Check OOMMonitor")
            
        elif index == 4:
            print("Don't touch me!")
    
    
    #----------------------------------------------------------------------
    '''
    description:更新nis程序
    '''
    def update_nis(self):
        
        webapps_dir = ntpath.split(self.oldpath)[0]
        TOMCAT_HOME = ntpath.split(webapps_dir)[0]
        
        self.info("开始备份nis系统...")
        self.zip_dir(self.oldpath, r"%s/nis-backup %s.zip" % (TOMCAT_HOME, time.strftime('%Y-%m-%d %H-%M-%S', time.localtime(time.time()))))
        self.info("nis系统备份完成")
        try:
            if self.replace_all == True:
                self.info("更新模式为直接替换整个文件夹...")
                
                self.info("清空目录%s" % self.oldpath)
                shutil.rmtree(self.oldpath, True, None)
                self.info("目录%s清空完成" % self.oldpath)
                
                self.info("开始将新文件%s拷贝到%s下" % (self.newpath, self.oldpath))
                shutil.copytree(self.newpath, self.oldpath, True)
                self.info("文件拷贝完成！")
                
                self.info("开始清空work目录...")
                shutil.rmtree(r"%s/work" % TOMCAT_HOME, True, None)
                self.info("work目录清空成功，NIS更新结束!")
                
                return 
            else:
                self.info("更新模式为单文件分析...")
                self.info("开始分析文件目录结构...")
                alllist = walk_list(self.oldpath, self.newpath)
                
                self.info("开始更新...")
                self.procee_walklist(alllist)
                self.info("常规更新结束")
                
                self.process_force_delete_update_direcory()
                
                self.info("开始分析orcus_web.xml...")
                self.merge_orcusweb_xml()
#                 self.info("orcus_web.xml更新结束")
                self.info("orcus_web.xml更新提醒结束")
                
                self.info("开始分析diagnosis.xml...")
                self.merge_diagnosis_xml()
                self.info("diagnosis.xml更新提醒结束")
                
                self.info("开始清空work目录...")
                shutil.rmtree(r"%s/work" % TOMCAT_HOME, True, None)
                self.info("work目录清空成功！")
                
                self.info("NIS系统更新结束")
                return
            
        except Exception as ex:
            self.error("系统更新出错：%s" % ex)
        finally:
            self.line_finished()
    
    
    #----------------------------------------------------------------------
    '''
    description:处理force_delete_update_direcory目录
    '''
    def process_force_delete_update_direcory(self):
        for dir0 in self.force_delete_update_directory:
            old_path = self.oldpath.replace("/", "\\");
            new_path = self.newpath.replace("/", "\\");
            
            self.info("清空目录%s" % (old_path + "\\" + dir0))
            shutil.rmtree(old_path + "\\" + dir0, True, None)
            self.info("目录%s清空完成" % (old_path + "\\" + dir0))
            
            self.info("开始将新文件%s拷贝到%s下" % (new_path + "\\" + dir0, old_path + "\\" + dir0))
            shutil.copytree(new_path + "\\" + dir0, old_path + "\\" + dir0, True)
            self.info("文件拷贝完成！")
        return
            
            
            
            
    
    #----------------------------------------------------------------------
    '''
    description:获得配置文件
    '''
    def initconfig(self):
        config = configparser.ConfigParser()
        
        # self.logger.info("配置文件为：%s" % os.path.realpath(__file__))
        configfile = os.path.join(os.path.split(sys.path[0])[0], "nis_update.ini")
        
        config.read(configfile)
        if len(config.sections()) == 0:
            self.logger.info("LogFrame不使用配置文件，系统将自动初始化配置信息")
        elif len(config.sections()) > 1:
            self.logger.error("LogFrame配置文件配置错误！不允许多个配置项！系统将使用默认项 CODE:%s" % len(config.sections()))
        else:
            self.logger.info("LogFrame配置文件为：%s" % configfile)
            section = config.sections().pop()
            # 通过配置文件赋值
            for key in config[section]:
                if key in self.__dict__:
                    self.setattr(key, ast.literal_eval(config[section][key]))   
                    
    #----------------------------------------------------------------------
    '''
    description:压缩目录
    parameter：dirname  待压缩的目录
    paramete：zipfilename 压缩后文件名（包含路径）
    ''' 
    def zip_dir(self, dirname, zipfilename):
        self.info("待压缩目录为：%s    压缩后的文件名为：%s" % (dirname, zipfilename))
        if os.path.exists(dirname):
            filelist = []
            if os.path.isfile(dirname):
                filelist.append(dirname)
            else :
                for root, dirs, files in os.walk(dirname):
                    for name in files:
                        filelist.append(os.path.join(root, name))
                 
            zf = zipfile.ZipFile(zipfilename, "w", zipfile.zlib.DEFLATED)
            for tar in filelist:
                arcname = tar[len(dirname):]
                zf.write(tar, arcname)
            zf.close()
            self.info("目录%s压缩完成" % dirname)
        else:
            self.info("目录%s不存在" % dirname)
            
    #----------------------------------------------------------------------        
    '''
    description:清空目录；删除文件：os.remove(filename)
    '''
    def delete_dir(self, dirname):
        self.info("开始清空目录%s" % dirname)
        shutil.rmtree(dirname, True, None)
        self.info("目录%s清空完成" % dirname)
    #----------------------------------------------------------------------
    
    '''
    description:diagnosis.xml
    '''
    def merge_diagnosis_xml(self):
        lfile = os.path.join(self.oldpath, self.merge_xml_files[1]).replace("\\", "/")
        self.info("原始diagnosis.xml文件路径为：%s" % lfile)
        
        rfile = os.path.join(self.newpath, self.merge_xml_files[1]).replace("\\", "/")
        self.info("新diagnosis.xml文件路径为：%s" % rfile)
        self.important("请用Beyond Compare工具更新WEB-INF\orcus\diagnosis.xml 和 WEB-INF\web.xml")
        
        
    '''
    description:合并orcus_web.xml文件
    '''    
    def merge_orcusweb_xml(self):
        lfile = os.path.join(self.oldpath, self.merge_xml_files[0]).replace("\\", "/")
        self.info("原始orcus_web.xml文件路径为：%s" % lfile)
        
        rfile = os.path.join(self.newpath, self.merge_xml_files[0]).replace("\\", "/")
        self.info("新orcus_web.xml文件路径为：%s" % rfile)
        
        self.update_orcusweb_xml(lfile, rfile)
    
    def contain_elementortask(self, tag, taglist):
        if tag.name == "element":
            for t in taglist:
                if t.name == "element" and t["key"].strip() == tag["key"].strip():
                    if tag["value"].strip() == t["value"].strip():
                        return True
                    else:
                        return "CNQ"  # contain but not equal
        elif tag.name == "task":
            for t in taglist:
                if t.name == "task" and tag.string.strip() == t.string.strip():
                    return True
        return False
    
    def process_element(self, all_element_tags):
        if len(all_element_tags) == 0:
            return
    
        element_parent = all_element_tags[0][0].parent
        for tag in all_element_tags:
            if tag[1] and tag[2] and tag[3]:
                pass
            elif tag[1] and tag[2] and not tag[3]:
                if tag[0]["key"].strip() in self.must_update_element_keys:
                    self.important("key=%s的element元素为必须更新的元素，请更新" % tag[0]["key"].strip())
#                     self.info("key=%s的element元素为必须更新的元素，所以更新" % tag[0]["key"].strip())
#                     tag[0]["value"] = tag[4]["value"]
                # 新的(right)值与旧的(left)值不一致，新的替换旧的
                else:
                    if self.is_exclusion_element(tag[0]["value"].strip()) or tag[0]["key"].strip() in self.exclusion_element_keys:
                        self.important("key=%s的element元素基本不需要更新，请慎重更改" % tag[0]["key"].strip())
#                         self.info("key=%s的element元素为受保护的元素，不进行更新" % tag[0]["key"].strip())
                    else:
                        self.important("key=%s的element元素的value属性不同，原始的为：%s，新的为：%s，请更新" % (tag[0]["key"].strip(), tag[0]["value"], tag[4]["value"]))
#                         self.info("key=%s的element元素的value属性不同，原始的为：%s，新的为：%s，将进行更新" % (tag[0]["key"].strip(), tag[0]["value"], tag[4]["value"]))
#                         tag[0]["value"] = tag[4]["value"]
            elif tag[1] and not tag[2]:
                # 旧的有，新的没有
                self.important("key=%s的element元素的在新版本中已被删除，请更新" % (tag[0]["key"].strip()))
                
#                 if self.BO_DELETE_ELEMENT:
#                     self.info("BO_DELETE_ELEMENT的配置为%s，所以删除新nis中没有的element元素%s" % (self.BO_DELETE_ELEMENT, tag[0]))
#                     tag[0].decompose()
#                 else:
#                     self.info("BO_DELETE_ELEMENT的配置为%s，所以保留新nis中没有的element元素%s" % (self.BO_DELETE_ELEMENT, tag[0]))
            elif not tag[1] and tag[2]:
                # 旧的没有，新的有
                self.important("key=%s的element元素的为新增加的元素，请更新" % (tag[0]["key"].strip()))
#                 if self.OC_UPDATE_ELEMENT:
#                     self.info("OC_UPDATE_ELEMENT的配置为%s，所以添加新nis中存在而旧nis中不存在的element元素%s" % (self.OC_UPDATE_ELEMENT, tag[0]))
#                     element_parent.append(tag[0])
#                 else:
#                     self.info("OC_UPDATE_ELEMENT的配置为%s，所以不添加新nis中存在而旧nis中不存在的element元素%s" % (self.OC_UPDATE_ELEMENT, tag[0]))
    
    def is_exclusion_element(self, tag_value):
        if self.VALUE_TRUE_FALSE_PROTECTED:
            return True
        elif tag_value == "true" or tag_value == "false":
            return False
        return True
            
    def process_task(self, all_task_tags):
        if len(all_task_tags) == 0:
            return
        task_parent = all_task_tags[0][0].parent
        
        for tag in all_task_tags:
            if tag[1] and tag[2]:
                pass
            if not tag[1] and tag[2]:
                self.important("task元素%s为新版本中增加的元素，请更新" % tag[0])
#                 if self.OC_UPDATE_TASK:
#                     self.info("OC_UPDATE_TASK的配置为%s，所以添加新nis中存在而旧nis中不存在的task元素%s" % (self.BO_DELETE_ELEMENT, tag[0]))
#                     task_parent.append(tag[0])
#                 else:
#                     self.info("OC_UPDATE_TASK的配置为%s，所以不添加新nis中存在而旧nis中不存在的task元素%s" % (self.BO_DELETE_ELEMENT, tag[0]))
            if tag[1] and not tag[2]:
                self.important("task元素%s为新版本中删除的元素，请更新" % tag[0])
#                 if self.BO_DELETE_TASK:
#                     self.info("BO_DELETE_TASK的配置为%s，所以删除新nis中不存在而旧nis中存在的task元素%s" % (self.BO_DELETE_ELEMENT, tag[0]))
#                     tag[0].decompose()
#                 else:
#                     self.info("BO_DELETE_TASK的配置为%s，所以保留新nis中不存在而旧nis中存在的task元素%s" % (self.BO_DELETE_ELEMENT, tag[0]))
    
    def filter_element(self, element_key):
            if element_key.strip() in self.exclusion_element_keys:
                return True
            else:
                return False 
            
    def update_orcusweb_xml(self, oldfile, newfile):
        
        lfile = oldfile
        rfile = newfile
        
        oldfile = open(lfile, 'r', encoding="UTF-8")
        soup = BeautifulSoup(oldfile, "xml")
        
        
        element_and_task_tags = SoupStrainer(["element", "task"])
        rsoup = BeautifulSoup(open(rfile, 'r', encoding="UTF-8"), "xml", parse_only=element_and_task_tags)
        
        all_element_tags = []
        allkeys = []
        for tag in soup("element"):
            d = [ tag, True, False, False, None ] 
            if  tag["key"] in allkeys:
                self.important("原始文件%s存在多个key值为%s的element元素，请修改（只能保留一个）" % (lfile, tag["key"]))
#                 self.info("原始文件%s存在多个key值为%s的element元素，程序将保留第一个" % (lfile, tag["key"]))
                tag.next_sibling.next_sibling.replace_with("")  # 注释
                tag.next_sibling.replace_with("")  # 换行符
                tag.decompose()
            else:
                all_element_tags.append(d)
                allkeys.append(tag["key"])
        
        for rtag in rsoup("element"):
            rd = [rtag, False, True, False, None]
            cmplist = [itemgetter(0)(i) for i in all_element_tags]
            if self.contain_elementortask(rd[0], cmplist) == "CNQ":
                index = allkeys.index(rd[0]["key"])
                all_element_tags[index][2] = True 
                all_element_tags[index][4] = rtag 
            elif self.contain_elementortask(rd[0], cmplist):
                index = allkeys.index(rd[0]["key"])
                all_element_tags[index][2] = True 
                all_element_tags[index][3] = True
            else:
                all_element_tags.append(rd)
                
        #--------------------------------------------------------------
        all_task_tags = []
        all_task_string = []
        for tag in soup("task"):
            d = [ tag, True, False]
            if tag.string.strip() in all_task_string:
                self.important("原始文件%s存在多个值为%s的task元素，请修改（只能保留一个）" % (lfile, tag.string.strip()))
#                 self.info("原始文件%s存在多个值为%s的task元素，程序将保留第一个" % (lfile, tag.string.strip()))
#                 tag.decompose()
            else:
                all_task_tags.append(d)
                all_task_string.append(tag.string.strip())
        
        for rtag in rsoup("task"):
            rd = [rtag, False, True]
            cmp_list = [itemgetter(0)(i) for i in all_task_tags]
            if self.contain_elementortask(rd[0], cmp_list):
                index = all_task_string.index(rd[0].string.strip())
                all_task_tags[index][2] = True 
            else:
                all_task_tags.append(rd)
        #----------------------------------------------------------------
        
        self.process_element(all_element_tags)
        self.process_task(all_task_tags)
        
        
        oldfile.close()
        
#         self.info("开始将更新写入%s..." % lfile)
#         orcusweb_xml = soup.prettify("utf-8")
#         orcusweb_xml = soup.prettify("utf-8", formatter=None)
#         
#         with open(lfile, "wb") as file:
#             file.write(orcusweb_xml)
#         self.info("写入成功")
#         
#         return orcusweb_xml
    
    
    #----------------------------------------------------------------------
    '''
    description:往Text元素里面写内容，并生成日志文件
    '''
    def info(self, msg):
        self.logger.info(msg)
        self.T.insert(tk.END, time.strftime(self.ISOTIMEFORMAT, time.localtime()) + "\n" + str(msg) + "\n\n" , "color_info")
        self.T.update()
        self.T.see(tk.END)
        
    def error(self, msg):
        self.logger.error(msg)
        self.T.insert(tk.END, time.strftime(self.ISOTIMEFORMAT, time.localtime()) + "\n" + str(msg) + "\n\n" , "color_error")
        self.T.update()
        self.T.see(tk.END)
        
    def line(self):
        self.T.insert(tk.END, "\n" + 52 * "-" + "\n\n", "center")
        self.T.update()
        self.T.see(tk.END)
        
    def important(self, msg):
        self.logger.info(msg)
        self.T.insert(tk.END, time.strftime(self.ISOTIMEFORMAT, time.localtime()) + "\n" + str(msg) + "\n\n" , "color_important")
        self.T.update()
        self.T.see(tk.END)
        
        
    def line_finished(self):
        self.logger.info("=======================================================\n")
        self.T.insert(tk.END, "\n" + 23 * "-" + "finished" + 23 * "-" + "\n\n", "center")
        self.T.update()
        self.T.see(tk.END)
        
    #----------------------------------------------------------------------    
        
    '''
    description:alllist来自于 walk_list
    '''
    def procee_walklist(self, alllist):
        olddir = self.oldpath
        newdir = self.newpath
        for flist in alllist:
            if self.filter_special(flist[0]):
                self.info("需要特殊处理(受保护或待合并或待处理)的文件%s，已跳过" % flist[0])
                continue;
            if flist[1]:
                # 文件
                if flist[2] and flist[3] and flist[4]:
                    self.info("相同的文件%s，已跳过" % flist[0])
                elif flist[2] and flist[3] and not flist[4]:
                    # 都存在但不同， 用right替换left
                    self.info("文件都存在，但不同，用新文件替换旧文件%s" % flist[0])
                    shutil.copyfile(newdir + flist[0], olddir + flist[0])
                elif not flist[2] and flist[3]:
                    # left不存在，right复制到left
                    oldnewpath = ntpath.split(olddir + flist[0])[0]
                    os.makedirs(oldnewpath, mode=0o777, exist_ok=True)
                    shutil.copy(newdir + flist[0], oldnewpath)
                    self.info("新文件：%s，已复制" % flist[0])
                elif flist[2] and not flist[3]:
                    # left 存在，right不存在，保留left
                    if self.BO_DELETE_FILE:
                        self.info("BO_DELETE_FILE的值为%s，所以删除旧nis存在而新nis不存在的文件%s" % (self.BO_DELETE_FILE, flist[0]))
                        os.remove(olddir + flist[0])
                    else:
                        self.info("BO_DELETE_FILE的值为%s，所以保留旧nis存在而新nis不存在的文件%s" % (self.BO_DELETE_FILE, flist[0]))
            else:
                # 空目录
                if self.filter_special_dir(flist[0]):
                    self.info("需要特殊处理(受保护或待合并或待处理)的目录%s，已跳过" % flist[0])
                    continue;
                if flist[2] and flist[3]:
                    # 都存在，啥都不做
                    pass
                elif flist[2] and not flist[3]:
                    # left存在，right不存在，则left维持原样
                    if self.BO_DELETE_EMPTY_DIR:
                        self.info("BO_DELETE_EMPTY_DIR的值为%s，所以删除旧nis存在而新nis不存在的空文件夹%s" % (self.BO_DELETE_EMPTY_DIR, flist[0]))
                        os.rmdir(olddir + flist[0])
                    else:
                        self.info("BO_DELETE_EMPTY_DIR的值为%s，所以保留旧nis存在而新nis不存在的空文件夹%s" % (self.BO_DELETE_EMPTY_DIR, flist[0]))
                elif not flist[2] and flist[3]:
                    # left不存在，right存在，则在left也创建新目录
                    os.makedirs(olddir + flist[0], mode=0o777, exist_ok=True)
                    self.info("空目录：%s，已创建" % flist[0])
           
    #----------------------------------------------------------------------    
    '''
    description:是否在目录中
    '''
    def is_in_dir(self, directory, file):
        if not len(directory) > 1:
            return False
        if file[0:1] == "\\":
            file = file[1:]
        if file[:len(directory) + 1] == directory + "\\":
            return True
        return False
    
    '''
    description:是否在目录集合中
    '''
    def is_in_dirs(self, directorys, file):
        if not len(directorys) > 0:
            return False
        if file[0:1] == "\\":
            file = file[1:]
        for directory in  directorys:
            if file[:len(directory) + 1] == directory + "\\":
                return True
        return False
    
    
    '''
    description:是否是排除的文件(merge_xml_files也算是排除的文件)
    '''
    def is_exclusion_file(self, file):
        if file[0:1] == "\\":
            file = file[1:]
        if file in self.exclusion_files:
            return True
        return False
        
    
    '''
    return 返回被exclusion_dirs过滤过的exclusion_files列表
    '''
    def exclusion_merge(self): 
        for must_delete_update_dir in self.force_delete_update_directory:
            if must_delete_update_dir not in self.exclusion_dirs:
                self.exclusion_dirs.append(must_delete_update_dir)
        temp = []
        for file in self.exclusion_files:
            for directory in self.exclusion_dirs:
                if not self.is_in_dir(directory, file):
                    temp.append(file)
                    
        for f in self.merge_xml_files:
            if f not in temp:
                temp.append(f)
                
        self.exclusion_files = temp
        
        for k in self.must_update_element_keys:
            if k in self.exclusion_element_keys:
                self.exclusion_element_keys.remove(k)
    
    '''
    description:是否是procee_walklist不需要处理的文件
    '''
    def filter_special(self, oldfile):
        if self.is_in_dirs(self.exclusion_dirs, oldfile):
            return True
        elif self.is_exclusion_file(oldfile):
            return True
        else:
            return False 
        
    def filter_special_dir(self, olddir):
        if olddir[0:1] == "\\":
            olddir = olddir[1:]
        if olddir in self.exclusion_dirs:
            return True
        return False

        
    #----------------------------------------------------------------------        
    '''
    description:设置类的属性
    '''            
    def setattr(self, name, value):
        self.__dict__[name] = value 
             
    #----------------------------------------------------------------------
    def onClose(self):
        """
        closes the frame and sends a message to the main frame
        """
        self.destroy()
        pub.sendMessage("logFrameClosed", arg1="data")
        
#----------------------------------------------------------------------


class Application(tk.Frame):
    """"""
    
#     labelbuttons = ['  单击选择当前nis文件夹...', '  单击选择新nis文件夹...', '更 新', 'OOMMonitor', '']
#     normal bold italic
#     fonts = [('楷体', 18, 'normal'), ('楷体', 18, 'normal'), ('宋体', 24, 'italic'), ('times', 24, 'italic'), ('times', 24, 'italic')]

    labelbuttons = ['Open current nis directory...', 'Open new nis directory...', 'Update', 'OOMMonitor', '']
#     normal bold italic
    fonts = [('times', 12, 'normal'), ('times', 12, 'normal'), ('times', 24, 'italic'), ('times', 24, 'italic'), ('times', 24, 'italic')]
    labelbitmaps = ['', '', 'hourglass', '', 'questhead']
    textalign = [tk.CENTER, tk.CENTER, tk.CENTER, tk.CENTER, tk.CENTER ]
    bitmapalign = [tk.LEFT, tk.LEFT, tk.LEFT, tk.LEFT, tk.LEFT]
      
    #----------------------------------------------------------------------
    def __init__(self, master=None):
        """Constructor"""
        tk.Frame.__init__(self, master)
        self.pack()
        self.root = master
        
        self.oldpath = ""
        self.newpath = ""
        # 日志配置 若为0 则只产生一个日志文件，且backupCount失效
        self.maxMegabytes = 10
        self.backupCount = 5
        
        self.logger = self._getLogger()
        self.initconfig()  # 由于initconfig里面使用日志记录，所以日志没法配置，如果要使日志可配置，请取消initconfig()中的日志记录。
        
        
        createBitmap(master)
        self.pack()
        
        self.mainview()
        self.pack()
        
  
        pub.subscribe(self.listener, "logFrameClosed")
  
    #----------------------------------------------------------------------
    def listener(self, arg1, arg2=None):
        """
        pubsub listener - opens main frame when logFrame closes
        """
        self.show()
  
    #----------------------------------------------------------------------
    def hide(self):
        """
        hides main frame
        """
        self.root.withdraw()
  
    #----------------------------------------------------------------------
    def openFrame(self, index=None):
        """
        opens other frame and hides main frame
        """
        self.hide()
        subFrame = LogFrame(index, self.oldpath, self.newpath, self.logger)
  
    #----------------------------------------------------------------------
    def show(self):
        """
        shows main frame
        """
        self.root.update()
        self.root.deiconify()
        
    #----------------------------------------------------------------------
    '''
    description:获得配置文件
    '''
    def initconfig(self):
        config = configparser.ConfigParser()
        
        # self.logger.info("配置文件为：%s" % os.path.realpath(__file__))
        configfile = os.path.join(os.path.split(sys.path[0])[0], "nis_update.ini")
        
        config.read(configfile)
        if len(config.sections()) == 0:
            self.logger.info("不使用配置文件，系统将自动初始化配置信息")
        elif len(config.sections()) > 1:
            self.logger.error("配置文件配置错误！不允许多个配置项！系统将使用默认项 CODE:%s\n==================================" % len(config.sections()))
        else:    
            self.logger.info("配置文件为：%s" % configfile)
            section = config.sections().pop()
            # 通过配置文件赋值
            for key in config[section]:
                if key in self.__dict__:
                    self.setattr(key, ast.literal_eval(config[section][key]))   
                    
    #----------------------------------------------------------------------
    '''
    description:日志初始化
    '''
    def _getLogger(self):
          
        logger = logging.getLogger('[NIS-UPDATE]')  
          
        handler = logging.handlers.RotatingFileHandler(os.path.join(os.path.split(sys.path[0])[0], "NIS_UPDATE.LOG"), maxBytes=int(self.maxMegabytes) * 1024 * 1024, backupCount=int(self.backupCount))        
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')  
        handler.setFormatter(formatter)  
          
        logger.addHandler(handler)  
        logger.setLevel(logging.INFO) 
          
        return logger 
    
    #----------------------------------------------------------------------
    # 主界面
    def mainview(self):
        for i in range(5):
            ct = [random.randrange(256) for x in range(3)]
            brightness = int(round(0.299 * ct[0] + 0.587 * ct[1] + 0.114 * ct[2]))
            ct_hex = "%02x%02x%02x" % tuple(ct)
            bg_colour = '#' + "".join(ct_hex)
            
            l = tk.Label(self.root, text=self.labelbuttons[i], fg='White' if brightness < 120 else 'Black', anchor=self.textalign[i], bg=bg_colour, compound=self.bitmapalign[i], bitmap=self.labelbitmaps[i])
            
            if i >= 2:
                l.config(font=self.fonts[i])
                
            space = lambda x: x > 2 and 20 or 0
            l.place(x=50, y=80 + i * 50 + space(i), width=300, height=40)
            l.bind('<Button-1>', lambda event, arg=l, index=i: self.click(event, arg, index))
    
    #----------------------------------------------------------------------
    '''
    description:处理单击事件
    '''
    def click(self, event, this, index):
        
        def getPathName(pathname, title):
            name = filedialog.askdirectory(initialdir="D:\\runtime\\tomcat-6.0.29\\webapps\\nis", title=title)
            if len(name) != 0:
                self.setattr(pathname, name)
                this["text"] = get_sub_str(name, 42)
                
        
        if index == 0:
            getPathName("oldpath", "选择旧nis文件夹\n例如：D:\\runtime\\tomcat-6.0.29\\webapps\\nis")
        elif index == 1:
            getPathName("newpath", "选择新nis文件夹\n例如：D:\\runtime\\nis")
        elif index == 2:
            if len(self.oldpath) > 0 and len(self.newpath) > 0:
                self.openFrame(2)
            else:
                messagebox.showerror("nis文件名不能为空", "nis文件名不允许为空\n请选择nis文件路径")
                
        else:
            self.openFrame(index)
            
    #----------------------------------------------------------------------        
    '''
    description:设置类的属性
    '''            
    def setattr(self, name, value):
        self.__dict__[name] = value 
#----------------------------------------------------------------------

root = tk.Tk()
center_window(root, w=400, h=400, title="自动更新nis系统  v1.0")
app = Application(master=root)
app.mainloop()
