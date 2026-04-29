"""
抖音 Cookies 配置说明

如何获取抖音 Cookies：

1. 打开浏览器（Chrome/Edge）
2. 访问 https://www.douyin.com/ 并登录你的抖音账号
3. 按 F12 打开开发者工具
4. 切换到 "Application" 或 "应用程序" 标签
5. 左侧选择 "Cookies" → "https://www.douyin.com"
6. 找到以下重要的 Cookie：
   - ttwid
   - __ac_nonce
   - __ac_signature
   - s_v_web_id
   - passport_csrf_token

7. 将这些 Cookie 保存到 douyin_cookies.txt 文件中，格式如下：

# Netscape HTTP Cookie File
.douyin.com	TRUE	/	FALSE	0	ttwid	你的ttwid值
.douyin.com	TRUE	/	FALSE	0	__ac_nonce	你的__ac_nonce值
.douyin.com	TRUE	/	FALSE	0	__ac_signature	你的__ac_signature值
.douyin.com	TRUE	/	FALSE	0	s_v_web_id	你的s_v_web_id值
.douyin.com	TRUE	/	FALSE	0	passport_csrf_token	你的passport_csrf_token值

或者使用浏览器插件：
- Chrome: "Get cookies.txt LOCALLY" 插件
- Firefox: "cookies.txt" 插件

导出后将文件保存为 backend/douyin_cookies.txt
"""
