# 盲评包

请勿打开另存的 key.json。只依据答案正文逐条评分：0=未覆盖或错误，1=部分覆盖，2=完整且正确。
正分需摘录正文中的原句；不得把来源附录、题目或模型信心当作答案。保持分歧，不强行合并。
请填写 blind_review.json 的 ratings、reviewer 和 review_date；没有事实条目的题填写 question_judgment（完整/部分/拒答/错误）及备注。
单事实例外单独报告，不进入主事实覆盖均值。技术产品版本号保留；评测系统身份信息未提供。

## B001

```text
What exactly is "wpcollector" in WebSphere Portal Server?
I've been told to get wpcollector output? What exactly is this?
```

答案正文：

```text
2. If you did not FTP your files via wpcollector, locate the "wp.mustgather.zip" file or the "<pmr #>-wp.mustgather-timestamp.zip" file in <wp_profile_root> [https://idoc2.swg.usma.ibm.com/portal/topic/com.ibm.wp.ent.doc_v70/reference/wpsdirstr.html#wpsdirstr__wp_profile_root]/filesForAutoPD/. Send the files to IBM Support by using the instructions outlined in Exchanging information with IBM Technical Support for problem determination [http://www-01.ibm.com/support/docview.wss?rs=688&uid=swg21201571]. 

Note: When sending in logs for review, include any console output from the ConfigEngine command that might be useful. 

Option B: Manual collection of troubleshooting data 

If you are unable to use wpcollector for WebSphere Portal for automatic log collection, use the following instructions for manually collecting the necessary information. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Wpcollector is a command line tool that automates the collection of portal logs and configuration files. |  |  |
| F2 | Using automated log collection early in the Case life cycle can greatly reduce the number of doc requests that are made by Support. |  |  |

评审人：________　日期：________　整题判断：________

## B002

```text
Security Bulletin: IBM MQ and IBM MQ Appliance Shared memory leak caused by MQ applications using dynamic queues (CVE-2017-1283)
I need to understand details regarding Security Bulletin: IBM MQ and IBM MQ Appliance Shared memory leak caused by MQ applications using dynamic queues (CVE-2017-1283). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2017-1283 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-1283]
DESCRIPTION: IBM WebSphere MQ could allow an authenticated user to cause a shared memory leak by MQ applications using dynamic queues, which can lead to lack of resources for other MQ applications.
CVSS Base Score: 3.1
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/125144 [https://exchange.xforce.ibmcloud.com/vulnerabilities/125144] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:N/A:L) 

AFFECTED PRODUCTS AND VERSIONS
IBM MQ V8
IBM MQ 8.0.0.0 - 8.0.0.6 maintenance levels
IBM MQ Appliance V8
IBM MQ Appliance 8.0.0.0 - 8.0.0.6 maintenance levels
IBM MQ V9
IBM MQ 9.0.0.0 - 9.0.0.1 maintenance levels
IBM MQ V9 CD
IBM MQ 9.0.1 - 9.0.3 releases
IBM MQ Appliance V9 CD
IBM MQ Appliance 9.0.1 - 9.0.3

REMEDIATION/FIXES
IBM MQ V8 

Apply Fix Pack 8.0.0.7 [https://www-01.ibm.com/support/docview.wss?uid=swg22005832]
IBM MQ Appliance V8
Apply Fix Pack 8.0.0.7 for MQ Appliance [https://www-01.ibm.com/support/docview.wss?uid=swg22005832]
IBM MQ V9
Apply Fix Pack 9.0.0.2 [http://www-01.ibm.com/support/docview.wss?uid=swg24044038]
IBM MQ V9 CD
Upgrade to IBM MQ 9.0.4 [http://www-01.ibm.com/support/docview.wss?uid=swg24043348]
IBM MQ Appliance V9 CD
Upgrade to IBM MQ Appliance 9.0.4 [http://www-01.ibm.com/support/docview.wss?uid=swg24043348]

WORKAROUNDS AND MITIGATIONS
None. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM WebSphere MQ could allow an authenticated user to cause a shared memory leak by MQ applications using dynamic queues, which can lead to lack of resources for other MQ applications |  |  |
| F2 | CVSS Base Score: 3.1 |  |  |
| F3 | (CVSS:3.0/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:N/A:L) |  |  |

评审人：________　日期：________　整题判断：________

## B003

```text
Help with Security Bulletin: WMB and IIB Toolkit cannot connect to a remote WMB broker or IIB node with a TLS-compliant cipher (CVE-2015-0118)
I need to understand details regarding Security Bulletin: WebSphere Message Broker Toolkit and IBM Integration Toolkit cannot connect to a remote WebSphere Message Broker broker or IBM Integration Bus node with a TLS-compliant cipher (CVE-2015-0118). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2015-0118 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-0118]
DESCRIPTION: IBM Integration Toolkit cannot connect to a remote IBM Integration Bus node with a TLS-compliant cipher because the IBM MQ client JARs are back level. The connection fails because the IBM MQ client JAR files included with the toolkit do not support the stronger TLS cipher suites.
CVSS Base Score: 1.5
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/100349 [https://exchange.xforce.ibmcloud.com/vulnerabilities/100349] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:L/AC:M/Au:S/C:P/I:N/A:N) 

AFFECTED PRODUCTS AND VERSIONS
WebSphere Message Broker Toolkit V7 and V8. 

 IBM Integration Toolkit V9

REMEDIATION/FIXES
 

Product VRMF APAR Remediation/Fix IBM Integration Toolkit V9.0 IT05725 9003 Interim Fix 001 WebSphere Message Broker 
Toolkit V8.0 IT05725 8005 Interim Fix 001 WebSphere Message Broker
Toolkit V7.0 IT05725 7007 Interim Fix 002 
Toolkit interim fixes can be installed via IBM Installation Manager. In Installation Manager, please make sure that the Search service repositories during installation and updates option in Preferences -> Repositories is checked. Then click Update in the main panel to install the interim fixes listed above. WORKAROUNDS AND MITIGATIONS
None [S1]
VULNERABILITY DETAILS
脆弱性の詳細
CVEID: CVE-2015-0118 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-0118]
DESCRIPTION: IBM Integration Toolkit cannot connect to a remote IBM Integration Bus node with a TLS-compliant cipher because the IBM MQ client JARs are back level. The connection fails because the IBM MQ client JAR files included with the toolkit do not support the stronger TLS cipher suites.
CVSS Base Score: 1.5
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/100349 [https://exchange.xforce.ibmcloud.com/vulnerabilities/100349] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:L/AC:M/Au:S/C:P/I:N/A:N) 

AFFECTED PRODUCTS AND VERSIONS
影響のある製品・バージョン： 

次の製品に影響があります。 

・WebSphere Message Broker Toolkit V7 and V8 

・IBM Integration Toolkit V9

REMEDIATION/FIXES
修正策：



製品 バージョン APAR 修正ファイル IBM Integration Toolkit V9.0 IT05725 9003 Interim Fix 001 WebSphere Message Broker 
Toolkit V8.0 IT05725 8005 Interim Fix 001 WebSphere Message Broker
Toolkit V7.0 IT05725 7007 Interim Fix 002 
ツールキットは、 IBM Installation Manager を使用して、Interim fix を導入します。IBM Installation Managerの 
設定 > リポジトリー の インストール中および更新｢中にサービスリポジトリーの検索 オプションにチェックし、、更新 をクリックし、 interim fix を導入してください。 WORKAROUNDS AND MITIGATIONS
回避策/軽減策： 

なし [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B004

```text
Invalid operation: result set is closed. ERRORCODE=-4470, SQLSTATE=null
When using BPM, I see runtime exceptions saying that this SQL error occurs: Invalid operation: result set is closed. ERRORCODE=-4470, SQLSTATE=null

For example:

CWLLG2015E: An unexpected runtime exception occurred. See exception for more details. Error: Wrapped com.lombardisoftware.core.TeamWorksRuntimeException:
```

答案正文：

```text
*  A fix is available for IBM BPM V8.5.5.0 that ensures an explicit
    transaction would be used.  Transaction would only be closed
   after data is completely read from database. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B005

```text
Why are some Datatypes corrupt after Impact cluster failover/failback ?
Running Impact 7.1.0.11. The symptom is whenever Impact does a failover, a couple DataTypes
turn out empty.

I've checked the type files before and after Impact failover and the difference happens in the property

*.SQL.USERPARAMETERS

This property no longer exists for the corrupted datatypes".
```

答案正文：

```text
*  Work- around ...
   
   set impact.cluster.readlimit to 32768 at least.
   
   Update <SERVERNAME>_server.props files both
   on Primary and Backup and
   restart the server.
   You might have to delete the corrupt property files
   
   for the Backup to grab the new ones from the Primary.
   
   
    
   
   

PROBLEM SUMMARY
 *  TBSM 6.1 Failover system fails to restart.
   configuratrion files were corrupted in
    /opt/IBM/tivol/tbsm/etc [S4]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Add the property to $NCHOME/impact/etc/<SERVERNAME>_server.props file where size limit can be 8192, 16384, 32768, etc.. |  |  |
| F2 | The property would have to be added to all ImpactServers in the Cluster and would require a restart to enable |  |  |
| F3 | ensure that there are no trailing white-space characters on the property |  |  |
| F4 | The APAR is not an issue in Impact 6 and 7, but one would still have to include this property with an appropriate value |  |  |
| F5 | The character length includes the whole USERPARAMETERS property name as well as the definition |  |  |

评审人：________　日期：________　整题判断：________

## B006

```text
What does the end-file-message mean while doing a launchpad.sh in the MS"
I am getting an end-file-message means while doing a launchpad.sh in the MS. How do I solve the problem?
```

答案正文：

```text
This error messag is seen because of some missing Linux libraries. Usually what's missing are the compat-libstdc++ or libstdc++ libraries. Usually the 32-bit version is missing. Use the commands shown below to verify you have them installed, otherwise contact your Linux system administrator and installt these required libraries. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Use the commands shown below to verify you have them installed, otherwise contact your Linux system administrator and installt these required libraries. |  |  |

评审人：________　日期：________　整题判断：________

## B007

```text
Help with Security Bulletin: TLS padding vulnerability affects IBM PureApplication System (CVE-2014-8730)
I need to understand details regarding "Security Bulletin: TLS padding vulnerability affects IBM PureApplication System (CVE-2014-8730)". Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2014-8730 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-8730]
DESCRIPTION: IBM PureApplication Server bundles IBM HTTP Server, which could allow a remote attacker to obtain sensitive information, caused by the failure to check the contents of the padding bytes when using CBC cipher suites of some TLS implementations. A remote user with the ability to conduct a man-in-the-middle attack could exploit this vulnerability via a POODLE (Padding Oracle On Downgraded Legacy Encryption) like attack to decrypt sensitive information and calculate the plain text of secure connections.
CVSS Base Score: 4.3
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/99216 [https://exchange.xforce.ibmcloud.com/vulnerabilities/99216] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:M/Au:N/C:P/I:N/A:N)

AFFECTED PRODUCTS AND VERSIONS

This vulnerability affects all versions and releases of IBM HTTP Server (powered by Apache) component in all editions of WebSphere Application Server and bundling products. IBM PureApplication Server bundles WebSphere Application Server in its Web Application Pattern.

IBM PureApplication System V1.1
IBM PureApplication System V2.0
IBM PureApplication System V2.1

REMEDIATION/FIXES
The solution is to apply an update to the Web Application pattern type included in IBM PureApplication System:

IBM PureApplication System V2.1 

 * 
 * 
 * http://www-933.ibm.com/support/fixcentral/swg/downloadFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.1.0.1&platform=All&function=fixId&fixids=webapp-2.0.4.1-sys&includeSupersedes=0
 * 
 * 
 * 
 * 
 * http://www-933.ibm.com/support/fixcentral/swg/downloadFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.1.0.1&platform=All&function=fixId&fixids=webapp-1.0.4.1-sys&includeSupersedes=0


IBM PureApplication System V2.0 

 * 
 * 
 * http://www-933.ibm.com/support/fixcentral/swg/downloadFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.0.0.1&platform=All&function=fixId&fixids=webapp-2.0.2.1-vaea-20150610&includeSupersedes=0


IBM PureApplication System V1.1 and earlier: 

 * 
 * 
 * 

You should verify applying this fix does not cause any compatibility issues. WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM PureApplication Server bundles IBM HTTP Server, which could allow a remote attacker to obtain sensitive information, caused by the failure to check the contents of the padding bytes when using CBC cipher suites of some TLS implementations |  |  |
| F2 | A remote user with the ability to conduct a man-in-the-middle attack could exploit this vulnerability via a POODLE (Padding Oracle On Downgraded Legacy Encryption) like attack |  |  |
| F3 | CVSS Base Score: 4.3 |  |  |
| F4 | (AV:N/AC:M/Au:N/C:P/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B008

```text
CQWEB  can\'t retrieve repository dropdown list options in RedHat Linux, how to deal with it ?
I setup a cq demo env in redhat linux with oracle database, CQ 7.1.2, LRKS 8.1.3,  Linux CQ client can login CQ as the following picture 1, but CQWEB login page can't retrieve the repository dropdown list options as the following picture 2.  I used cqreg to register CQ database:

cqreg add_dbset -v ORACLE -s 192.168.0.84 -d ESBDB -u cqadmin -p cqadmin -dbset CQ_DEMO_ORACLE -co LOB_TYPE=CLOB -force

What's matter for this happen?
```

答案正文：

```text
About the default database path: 
When ClearQuest tries to connect to a database, it will first look if the CQ_DATABASES variable has been set, and if set, it will use this variable to determine where the database is registered. With the setenv command, you can set a user or system variable. (This is under the cshell. If using bash, use the env command and then export the env variable with the export command.) If the default database path has not been set, you can set it by entering the variable CQ_DATABASES. This should point to:  * 
 * 
   /opt/rational/clearquest/CQDB_rgys/cqdb_registry/ [S1]
Run cqreg initialize. The add_dbset command will run successfully afterwards. However, should the same error persist, make sure the command is run as the root user. 



Also make sure that the CQ_DATABASES environment variable is set to the desired registry path. If it is not, set the variable accordingly, then run the previously mentioned commands again. [S6]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Normally, at the end of a ClearQuest installation on UNIX® based platforms, the cqreg initialize command runs automatically |  |  |
| F2 | The command creates the registry structure for database sets |  |  |
| F3 | During the installation, the command did not run successfully |  |  |

评审人：________　日期：________　整题判断：________

## B009

```text
Help with Security Bulletin: Vulnerability in Diffie-Hellman ciphers affects IBM WebSphere MQ Internet Passthru (CVE-2015-4000)
I need to understand details regarding Security Bulletin: Vulnerability in Diffie-Hellman ciphers affects IBM WebSphere MQ Internet Passthru (CVE-2015-4000). What is the recommended fix?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2015-4000 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-4000]
DESCRIPTION: The TLS protocol could allow a remote attacker to obtain sensitive information, caused by the failure to properly convey a DHE_EXPORT ciphersuite choice. An attacker could exploit this vulnerability using man-in-the-middle techniques to force a downgrade to 512-bit export-grade cipher. Successful exploitation could allow an attacker to recover the session key as well as modify the contents of the traffic. This vulnerability is commonly referred to as "Logjam".
CVSS Base Score: 4.3
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/103294 [https://exchange.xforce.ibmcloud.com/vulnerabilities/103294] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:M/Au:N/C:P/I:N/A:N) 

AFFECTED PRODUCTS AND VERSIONS
The affected ciphersuite is available in all versions of IBM WebSphere MQ Internet Pass-thru (MQIPT) prior to 2.1.0.2

REMEDIATION/FIXES
SupportPac MS81: IBM WebSphere MQ Internet Pass-Thru
Users of IBM WebSphere MQ Internet Pass-Thru 2.1.0.1, 2.0 and older releases should first upgrade to IBM WebSphere MQ Internet Pass-Thru 2.1.0.2 [http://www.ibm.com/support/docview.wss?uid=swg24006386].

WORKAROUNDS AND MITIGATIONS
None. [S1]
VULNERABILITY DETAILS
脆弱性の詳細
CVEID: CVE-2015-4000 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-4000]
DESCRIPTION: The TLS protocol could allow a remote attacker to obtain sensitive information, caused by the failure to properly convey a DHE_EXPORT ciphersuite choice. An attacker could exploit this vulnerability using man-in-the-middle techniques to force a downgrade to 512-bit export-grade cipher. Successful exploitation could allow an attacker to recover the session key as well as modify the contents of the traffic. This vulnerability is commonly referred to as "Logjam".
CVSS Base Score: 4.3
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/103294 [https://exchange.xforce.ibmcloud.com/vulnerabilities/103294] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:M/Au:N/C:P/I:N/A:N) 

AFFECTED PRODUCTS AND VERSIONS
影響のある製品・バージョン： 

次の製品に影響があります。 

・IBM WebSphere MQ Internet Pass-Thru (MQIPT) : SupportPac MS81 

2.1.0.2 以前のIBM WebSphere MQ Internet Pass-Thru (MQIPT) のすべてのバージョンで影響のある暗号スイートが使用されています。

REMEDIATION/FIXES
修正策： 


IBM WebSphere MQ Internet Pass-Thru 2.1.0.2 [http://www.ibm.com/support/docview.wss?uid=swg24006386] 以降のリリースにアップグレードしてください。

WORKAROUNDS AND MITIGATIONS
回避策/軽減策： 

なし [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Users of IBM WebSphere MQ Internet Pass-Thru 2.1.0.1, 2.0 and older releases should first upgrade to IBM WebSphere MQ Internet Pass-Thru 2.1.0.2 |  |  |

评审人：________　日期：________　整题判断：________

## B010

```text
Why Plug-in log file reports an error message after install & configure the WebSphere Plugin 8.5 version on a Apache 2.4 webserver.
During web server start-up, errors like the following will be logged into the Plug-in log file (http_plugin.log):

ERROR: lib_security: loadSecurityLibrary: Failed to load gsk library from /opt/IBM/WebSphere/Plugins/gsk8/gsk8_64 ERROR: ws_transport: transportInitializeSecurity: Unable to load security library ERROR: ws_server: serverAddTransport: Failed to initialize security ERROR: ws_server: serverAddTransport: HTTPS Transport is skipped

Note: This is after install & configure the WebSphere Plugin 8.5 version on a Apache 2.4 webserver  on a Linux platform
```

答案正文：

```text
To resolve the problem, you must set the LD_LIBRARY_PATH environment variable to point to the library directory of the GSKit that comes with the IBM web server Plug-in. The precise directory location will depend of the version of Plug-in, and on the bit depth being used (32-bit or 64-bit). [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | you must set the LD_LIBRARY_PATH environment variable |  |  |
| F2 | to point to the library directory of the GSKit that comes with the IBM web server Plug-in |  |  |
| F3 | The precise directory location will depend of the version of Plug-in, and on the bit depth being used (32-bit or 64-bit) |  |  |

评审人：________　日期：________　整题判断：________

## B011

```text
How to use the LIKE operator, wildcard and special characters in your IBM FileNet Content Platform Engine Sweep's Filter Expression?
```

答案正文：

```text
IBM How to use the LIKE operator, wildcard and special characters in your IBM FileNet Content Platform Engine Sweep's Filter Expression - United States

TECHNOTE (FAQ)

QUESTION
 How to use the LIKE operator, wildcard and special characters in your IBM FileNet Content Platform Engine Sweep's Filter Expression? 

CAUSE
A sweep is an instance of a background service that you configure to process objects in a database table or some other set of items. To optimize sweep performance, you can optionally make the filter expression for the sweep a part of the WHERE clause of the sweep query. This inclusion means that the sweep retrieves only those database rows that satisfy the filter conditions.
The criteria is expressed in terms of properties and values of the objects that are targeted by the sweep. The syntax is a subset of the SQL syntax for the WHERE clause. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B012

```text
Why is the test suite execution failing from Decision Center?
When executing a test suite from Decision Center the run may fail with an error message similar to:
 XU client error.
 GBRXU0448E: Plugin error.
 Unable to retrieve the engine manager.
 The parsing of the ruleset failed Problem occurred loading translation: Error when translating parameter "inputParameter": Cannot translate class "sample.InputParameter".

What can be causing this error?
```

答案正文：

```text
First, ensure that the XOM and its dependencies were compiled for a Java version that is compatible with the JVM running the server that hosts Rule Execution Server. For example, classes that are compiled to comply with a Java 7 target would not work on a Java 6 JVM. [S1]
1. If working with ODM 8.5.0, please upgrade to ODM v8.5.1 (which contains the fix for APAR RS01418 [http://www.ibm.com/support/docview.wss?uid=swg1RS01418]) or later, to allow users mapped to resdeployers and resmonitors roles to be able to retrieve the HTDS Description file as well. If unable to do so immediately, make sure the user is mapped to the resAdministrators role, which is mapped to the Monitor role on WebSphere Application Server.

2. Ensure that the JDK level used for compiling the Java XOM classes is the same as the JDK level of the JVM used to run the application server. For example, the XOM could be compiled with Java 7 but the application server could be using Java 6. [S3]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B013

```text
Security Bulletin: MQ Explorer directory created with owner '555' on Linux x86-64 vulnerability affects IBM MQ (CVE-2016-6089)
I need to understand details regarding Security Bulletin: MQ Explorer directory created with owner '555' on Linux x86-64 vulnerability affects IBM MQ (CVE-2016-6089). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS

CVEID:CVE-2016-6089 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-6089]
DESCRIPTION:IBM WebSphere MQ could allow a local user to write to a file or delete files in a directory they should not have access to due to improper access control.
CVSS Base Score: 4
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/117926 [https://exchange.xforce.ibmcloud.com/vulnerabilities/117926]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N) 

AFFECTED PRODUCTS AND VERSIONS
IBM MQ v9.0.0.0 

IBM MQ v9.0.1

REMEDIATION/FIXES
IBM MQ v9.0.1 

Apply IBM MQ v9.0.2 [https://www-01.ibm.com/support/docview.wss?uid=swg24043463] 

IBM MQ v9.0.0.0 

Apply IBM MQ v9.0.0.1 [https://www-01.ibm.com/support/docview.wss?uid=swg24043467]

WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B014

```text
How do I enable my Applications to show up in the App Health view for the WAS agent?
```

答案正文：

```text
(1) Right click on Application Health navigator item in the TEP 
(2) Select 'Situations' and then select 'WebSphere App Server' 
(3) Click on the icon to set Situation filter criteria (4 downward pointing arrows icon) 
(4) Tick the box 'Eligible for association' and select OK 
(5) Right click on WasAppDiscovered and select 'Associate' 
(6) Ok the situations box and close

You should be able to see all discovered applications at once in the Application Health Summary view at this point.

Alternatively you can run the Take Action Set_Application_Monitoring on specific applications this way: 

- Access the TEP, select the Navigator item "Application Health". Right click on this navigator item and select workspaces and then the workspace "Application Registry". 
- Right click on the applications that are presented and have a status of disabled or discovered in the view then select "take action". 
- Select the take action "Set_Application_Monitoring". All of the values for the take action will be filled in automatically. Change the value Mon_Status from 0 to 1 to enable Application monitoring. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B015

```text
Why get SQL1227N when replay db2look output on DB2 V9.7 FP11?
Why get below SQL1227N when replay db2look output on DB2 V9.7 FP11?

     -----
     UPDATE SYSSTAT.COLUMNS SET COLCARD=4, NUMNULLS=1, SUB_COUNT=-1, SUB_DELIM_LENGTH=-1, 
     AVGCOLLENCHAR=7, HIGH2KEY='', LOW2KEY='        ', AVGCOLLEN=12 WHERE COLNAME = 'COL1' 
     AND TABNAME = 'TAB1' AND TABSCHEMA = 'DB2INST1'
     DB21034E  The command was processed as an SQL statement because it was not a
     valid Command Line Processor command.  During SQL processing it returned:
     SQL1227N  The catalog statistic "" for column "HIGH2KEY" is out of range for
     its target column, has an invalid format, or is inconsistent in relation to
     some other statistic. Reason Code = "3".  SQLSTATE=23521
     -----
```

答案正文：

```text
Here is the SQL1227N message:
-----
UPDATE SYSSTAT.COLUMNS SET COLCARD=4, NUMNULLS=1, SUB_COUNT=-1, SUB_DELIM_LENGTH=-1, 
AVGCOLLENCHAR=7, HIGH2KEY='', LOW2KEY=' ', AVGCOLLEN=12 WHERE COLNAME = 'COL1' 
AND TABNAME = 'TAB1' AND TABSCHEMA = 'DB2INST1'
DB21034E The command was processed as an SQL statement because it was not a
valid Command Line Processor command. During SQL processing it returned:
SQL1227N The catalog statistic "" for column "HIGH2KEY" is out of range for
its target column, has an invalid format, or is inconsistent in relation to
some other statistic. Reason Code = "3". SQLSTATE=23521
-----
As above, UPDATE SYSSTAT.COLUMNS statement gets SQL1227N at col1 varchar(10).
It is caused by runstats, writes an unexpected HIGH2KEY and LOW2KEY statistic values.

Here is work arounds:

Work around #1
1. $ db2set DB2_STATISTICS=USCC:0
** this variable is available for V10.1 FP4 and above.
2. $ db2 terminate
3. $ db2start
4. $ repro.sh [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | It is an known limitation of current DB2 V9.7 and above versions' runstats |  |  |

评审人：________　日期：________　整题判断：________

## B016

```text
Why does my login fail when I use the ltpa-usrnm attribute?
You use a Domino server as your LDAP, and the login attribute you want to use is ltpa-usrnm. This is acceptable, as the login attribute can be set accordingly in the wimconfig.xml. When the search string is built for the login, it is in the form, cn=username, o=orgname.

This cause the following exception to the returned:

[3/30/16 9:56:03:453 CDT] 000000f7 exception E com.ibm.ws.wim.adapter.ldap.LdapConnection getAttributes CWWIM4520E The 'javax.naming.InvalidNameException: "CN=username/O=orgname": [LDAP: error code 34 - Invalid DN Syntax]; remaining name '"CN=username/O=orgname'";
```

答案正文：

```text
As the VMM behavior is working as designed in both cases by returning the respective exceptions, the issue can be corrected via one of the following methods: 

A) Remove or correct the value of the manager and/or secretary attribute in the LDAP so that it can be queried successfully.

B) Flag the manager and/or secretary attribute as unsupported, as shown on the Mapping Attributes [http://publib.boulder.ibm.com/infocenter/wpdoc/v6r1/index.jsp?topic=/com.ibm.wp.ent.doc_v6101/install/win_map_attributes.html] page of the WebSphere Portal 6.1 Information Center. This will have the effect that VMM will not use the property anymore, as it is virtually removed from VMM's configuration, and its values (even correct ones) cannot be read or written in LDAP. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | $AdminTask configureAdminWIMUserRegistry {-customProperties {"com.ibm.ws.wim.registry.allowDNPrincipalNameAsLiteral =true"} } |  |  |
| F2 | When this property is set, VMM determines whether the login name ends with a baseEntry; if not, it is not treated as a DN and login succeeds |  |  |
| F3 | The fix for this APAR is targeted for inclusion in fix packs 8.0.0.4 and 8.5.0.1 |  |  |

评审人：________　日期：________　整题判断：________

## B017

```text
Why is the reload() not clearing the attribute cache so I can see my newly updated LDAP data in real time?
You are leveraging the reload() functionality as described in the blog post:
  https://www.ibm.com/developerworks/community/blogs/PortalL2Thoughts/entry/how_to_programatically_refresh_data_from_ldap64?lang=en

to refresh the attribute cache after a change has been made to data within your LDAP. The purpose of this reload() is to update the data in real time on the Portal server. You discover that you are calling the reload(); however, the newly updated data is not immediately available to the application. How can this be fixed?
```

答案正文：

```text
ERROR DESCRIPTION
 *  PumaProfile.reload() enablement for VMM cache invalidation
   
   Use case:
   1) Customer logs into Portal with testuser
   2) Login for testuser pulls information from LDAP
   3) testuser information gets cached.
   4) testuser logs out
   5) Direct update is made to LDAP for testuser information
   6) testuser logs in successfully. However, "old" information is
   still
   cached and pulled, instead of new information pulled from LDAP.
   7) testuser information gets updated roughly 1 hour later once
   cached data times out
   
   This is working as designed with caching mechanisms.
   There is not a programmatic way to do this via the
   PUMA API at present time. The closest mechanism is the reload()
   method in the PumaProfile
   interface. However, this only bypasses the PUMA cache and still
   may pull from the VMM cache.
   
   This APAR adds additional configuration options to have
   PumaProfile.reload() method automatically invalidate LDAP
   Attribute cache in VMM LDAP Adapter. Please note that this
   invalidation to bypass caches is only triggered by
   PumaProfile.reload() method. Additionally, only the LDAP
   Attribute cache in VMM is invalidated. Puma Search operations
   are still answered from VMM caches.
   
   To enable WIM attribute cache invalidation during
   PumaProfile.reload() call, please use WAS Admin console ->
   Resources -> Resource environment providers -> 'WP
   PumaStoreService' to add new custom properties:
   
   WP PumaStoreService
   setting: store.puma_default.wim.cacheinvalidation.enabled
   values: [true|false]
   Use store.puma_default.wim.cacheinvalidation.enabled=true to
   enable the cache invalidation
   
   setting: store.puma_default.wim.cacheinvalidation.repositoryids
   values: <comma separated list of LDAP repository IDs as
   specified in wimconfig.xml>
   Use store.puma_default.wim.cacheinvalidation
   .repositoryids=<repositoryID> or
    store.puma_default.wim.cacheinvalidation
   .repositoryids=<repositoryID_1>,<repositoryID_2>,<repositoryID_3
   > to specify multiple WIM LDAP repository IDs.
   
   Please save changes and restart all server nodes afterwards.
   
   The IDs are specified in wimconfig.xml under
   <config:repositories> e.g.:
       <config:repositories xsi:type="config:LdapRepositoryType"
   adapterClassName="com.ibm.ws.wim.adapter.ldap.LdapAdapter"
           id="<repositoryID>"
   
   
   
   
   It may be possible to manually invoke the PumaProfile.reload()
   method through the use of custom code and the PUMA API. [S3]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This APAR fixes the issue. It clears the cache properly even if base entry is different than name in repository. |  |  |
| F2 | The fix for this APAR is currently targeted for inclusion in fix packs 8.0.0.13 and 8.5.5.9. |  |  |

评审人：________　日期：________　整题判断：________

## B018

```text
Unable to view batches in DotEdit
Hi all,

Is there any limitation to view batches in Dot Edit client application, because I am unable to see batches with QID more than 1119.

Also unable to see batches with status as "Pending".
```

答案正文：

```text
Please do the following: 

 1. Backup the \Datacap\DotEdit\apps.ini file. If the file does not exist, create a new one or copy it from \Datacap\tmweb.net. 
 2. Open it in notepad.exe or other editor. 
 3. Find the app to be modified (for example [APT]). If it does not exist, create a new section with the application name listed between square brackets. 
 4. Add a new line containing BatchLimit=xxx, where xxx is the number of batches to be displayed. 
 5. Save the file. [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Backup the \Datacap\DotEdit\apps.ini file |  |  |
| F2 | If the file does not exist, create a new one or copy it from \Datacap\tmweb.net |  |  |
| F3 | Find the app to be modified (for example [APT]). If it does not exist, create a new section with the application name listed between square brackets |  |  |
| F4 | Add a new line containing BatchLimit=xxx, where xxx is the number of batches to be displayed |  |  |
| F5 | Save the file |  |  |

评审人：________　日期：________　整题判断：________

## B019

```text
Help with Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808)
I need to understand details regarding Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
For vulnerability details, see the security bulletin Vulnerability in RC4 stream cipher affects IBM DB2 LUW (CVE-2015-2808). [http://www.ibm.com/support/docview.wss?uid=swg21717865]

AFFECTED PRODUCTS AND VERSIONS
 

Principal Product and Version(s) Affected Supporting Product and Version WebSphere Remote Server version V6.2, 6.2.1, 7.0, 7.1, 7.1.1, 7.1.2, 8.5 IBM DB2 Workgroup Server Edition 
V9.5, 9.7, 10.1, 10.5 [S1]
VULNERABILITY DETAILS
For vulnerability details, see the security bulletin Vulnerabilities in GSKit affect IBM® DB2® (CVE-2015-0138, CVE-2015-0159 and CVE-2014-6221). [http://www.ibm.com/support/docview.wss?uid=swg21699543]

AFFECTED PRODUCTS AND VERSIONS
 

Principal Product and Version(s) Affected Supporting Product and Version WebSphere Remote Server version V6.2, V6.2.1, 7.0, 7.1, 8.5 IBM DB2 Workgroup Server Edition 
V9.5, 9.7, 10.1, 10.5 [S6]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B020

```text
Help with Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808)
I need to understand details regarding Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
For vulnerability details, see the security bulletin Vulnerability in RC4 stream cipher affects IBM DB2 LUW (CVE-2015-2808). [http://www.ibm.com/support/docview.wss?uid=swg21717865]

AFFECTED PRODUCTS AND VERSIONS
 

Principal Product and Version(s) Affected Supporting Product and Version WebSphere Remote Server version V6.2, 6.2.1, 7.0, 7.1, 7.1.1, 7.1.2, 8.5 IBM DB2 Workgroup Server Edition 
V9.5, 9.7, 10.1, 10.5 [S1]
VULNERABILITY DETAILS
Consult these security bulletins 
[http://www-01.ibm.com/support/docview.wss?uid=swg21717865&myns=swgimgmt&mynp=OCSSEPGG&mynp=OCSSEPDU&mync=E&cm_sp=swgimgmt-_-OCSSEPGG-OCSSEPDU-_-E] 
Vulnerability in RC4 stream cipher affects IBM® DB2® LUW (CVE-2015-2808) [http://www-01.ibm.com/support/docview.wss?uid=swg21717865&myns=swgimgmt&mynp=OCSSEPGG&mynp=OCSSEPDU&mync=E&cm_sp=swgimgmt-_-OCSSEPGG-OCSSEPDU-_-E]
[http://www-01.ibm.com/support/docview.wss?uid=swg21717865&myns=swgimgmt&mynp=OCSSEPGG&mynp=OCSSEPDU&mync=E&cm_sp=swgimgmt-_-OCSSEPGG-OCSSEPDU-_-E] 
Vulnerability in RC4 stream cipher affects WebSphere Application Server (CVE-2015-2808) [http://www-01.ibm.com/support/docview.wss?uid=swg21701503&myns=swgws&mynp=OCSSEQTP&mync=E&cm_sp=swgws-_-OCSSEQTP-_-E]

for vulnerability details and information about fixes.

AFFECTED PRODUCTS AND VERSIONS
 

Principal Product and Version(s) Affected Supporting Product and Version Financial Transaction Manager v2.0 WebSphere Application Server 7.0
DB2 Enterprise Server Edition 9.7 Financial Transaction Manager v2.1 WebSphere Application Server 8.0
DB2 Enterprise Server Edition 9.7 Financial Transaction Manager v3.0 WebSphere Application Server 8.5.5
DB2 Enterprise Server Edition 10.1 [S3]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B021

```text
How can I alleviate performance problems with the octigate database?
ITCAM-related question: How can I alleviate performance problems with the octigate database?
```

答案正文：

```text
Typically performance problems are exhibited by system slowness, record locks, high CPU, slow command response time, system freezing up, etc.. etc.. Do a top (or topas) on your system, look for the top processes consuming high CPU. If you see any db2 processes, look in the regular DB2 db2diag.log for messages related to DB2 errors. If you see high CPU usage or performance issues on the DB2 server running the octigate database, you have few options on how to fix this.
The most common symptom we've seen when performance problems happen is when the number of records in the METHOD/REQUEST/MEMORYDATA is high (approx. 5M to 7M or higher records in any table), the subsequent inserts/updates into the tables gets much slower leading to performance issues. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B022

```text
Why is the reload() not clearing the attribute cache so I can see my newly updated LDAP data in real time?
You are leveraging the reload() functionality as described in the blog post:
  https://www.ibm.com/developerworks/community/blogs/PortalL2Thoughts/entry/how_to_programatically_refresh_data_from_ldap64?lang=en

to refresh the attribute cache after a change has been made to data within your LDAP. The purpose of this reload() is to update the data in real time on the Portal server. You discover that you are calling the reload(); however, the newly updated data is not immediately available to the application. How can this be fixed?
```

答案正文：

```text
ERROR DESCRIPTION
 *  PumaProfile.reload() enablement for VMM cache invalidation
   
   Use case:
   1) Customer logs into Portal with testuser
   2) Login for testuser pulls information from LDAP
   3) testuser information gets cached.
   4) testuser logs out
   5) Direct update is made to LDAP for testuser information
   6) testuser logs in successfully. However, "old" information is
   still
   cached and pulled, instead of new information pulled from LDAP.
   7) testuser information gets updated roughly 1 hour later once
   cached data times out
   
   This is working as designed with caching mechanisms.
   There is not a programmatic way to do this via the
   PUMA API at present time. The closest mechanism is the reload()
   method in the PumaProfile
   interface. However, this only bypasses the PUMA cache and still
   may pull from the VMM cache.
   
   This APAR adds additional configuration options to have
   PumaProfile.reload() method automatically invalidate LDAP
   Attribute cache in VMM LDAP Adapter. Please note that this
   invalidation to bypass caches is only triggered by
   PumaProfile.reload() method. Additionally, only the LDAP
   Attribute cache in VMM is invalidated. Puma Search operations
   are still answered from VMM caches.
   
   To enable WIM attribute cache invalidation during
   PumaProfile.reload() call, please use WAS Admin console ->
   Resources -> Resource environment providers -> 'WP
   PumaStoreService' to add new custom properties:
   
   WP PumaStoreService
   setting: store.puma_default.wim.cacheinvalidation.enabled
   values: [true|false]
   Use store.puma_default.wim.cacheinvalidation.enabled=true to
   enable the cache invalidation
   
   setting: store.puma_default.wim.cacheinvalidation.repositoryids
   values: <comma separated list of LDAP repository IDs as
   specified in wimconfig.xml>
   Use store.puma_default.wim.cacheinvalidation
   .repositoryids=<repositoryID> or
    store.puma_default.wim.cacheinvalidation
   .repositoryids=<repositoryID_1>,<repositoryID_2>,<repositoryID_3
   > to specify multiple WIM LDAP repository IDs.
   
   Please save changes and restart all server nodes afterwards.
   
   The IDs are specified in wimconfig.xml under
   <config:repositories> e.g.:
       <config:repositories xsi:type="config:LdapRepositoryType"
   adapterClassName="com.ibm.ws.wim.adapter.ldap.LdapAdapter"
           id="<repositoryID>"
   
   
   
   
   It may be possible to manually invoke the PumaProfile.reload()
   method through the use of custom code and the PUMA API. [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This APAR fixes the issue. It clears the cache properly even if base entry is different than name in repository. |  |  |
| F2 | The fix for this APAR is currently targeted for inclusion in fix packs 8.0.0.13 and 8.5.5.9. |  |  |

评审人：________　日期：________　整题判断：________

## B023

```text
Can I disable RC4 cyphers in TIP?
How can one disable the RC4 cypers in Tivoli Integrated Portal?
```

答案正文：

```text
To remove RC4 ciphers:


 1. Log into the Websphere Application server and navigate to:
    SSL certificate and key management > SSL configurations > NodeDefaultSSLSettings > Quality of protection (QoP)
    
    
 2. Select the *RC4* ciphers from the "Selected ciphers" list, and then click the "<<Remove" button.
    
    
 3.  Click the "Apply" button, and then the "Save (to the master configuration)" link.
    
    
 4. Restart TIP. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Log into the Websphere Application server and navigate to: SSL certificate and key management > SSL configurations > NodeDefaultSSLSettings > Quality of protection (QoP) |  |  |
| F2 | Select the *RC4* ciphers from the "Selected ciphers" list, and then click the "<<Remove" button |  |  |
| F3 | Click the "Apply" button, and then the "Save (to the master configuration)" link |  |  |
| F4 | Restart TIP |  |  |

评审人：________　日期：________　整题判断：________

## B024

```text
How do I change from shared to unshared connection?
in WAS, how do I change from shared to unshared connection. I am seeing connections max out and take a long time to release.
```

答案正文：

```text
intended to allow control over connection sharing for direct
   look-ups. If resource references are configured for this
   datasource/connection factory they will take precedence over
   this property and the resource ref settings will be used.
   For example: if an application is doing direct look-ups and
   unshared connections are desired set this property to unshared.
   
   The globalConnectionTypeOverride will have precedence over all
   other connection sharing settings.  For example if you set
   this property to unshared all connection requests will be
   unshared, both direct look-ups and resource reference lookups.
   The intended use for this property is  to  offer a quick way
   to test what the consequences would be of moving all
   connections for a particular datasoure/connection factory to
   unshared or shared. Currently the only was to achieve this [S3]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B025

```text
Should I upgrade to Oracle JDK 8 if I am using IBM Mobile Foundation, IBM Worklight, IBM Worklight Foundation, or IBM MobileFirst Platform Foundation products?
These is an upgrade available to replace Oracle JDK 7 with Oracle JDK 8. Does IBM Mobile Foundation, IBM Worklight, IBM Worklight Foundation, and the IBM MobileFirst Platform Foundation products support the use of Oracle JDK 8?
```

答案正文：

```text
知识库无法回答该问题。
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The IBM Mobile Foundation, IBM Worklight, IBM Worklight Foundation, and IBM MobileFirst Platform Foundation products support Oracle JDK 7, but do not support Oracle JDK 8. |  |  |

评审人：________　日期：________　整题判断：________

## B026

```text
Help with Security Bulletin: IBM WebSphere MQ is affected by a privilege escalation vulnerability (CVE-2017-1612)
I need to understand details regarding Security Bulletin: IBM WebSphere MQ is affected by a privilege escalation vulnerability (CVE-2017-1612).
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2017-1612 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-1612]
DESCRIPTION: IBM WebSphere MQ service trace module could be used to execute untrusted code under 'mqm' user
CVSS Base Score: 7.4
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/132953 [https://exchange.xforce.ibmcloud.com/vulnerabilities/132953] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:L/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H) 

AFFECTED PRODUCTS AND VERSIONS
 

Product Affected Versions IBM WebSphere MQ 7.0.1.0 - 7.0.1.14 IBM WebSphere MQ 7.1.0.0 - 7.1.0.8 IBM WebSphere MQ 7.5.0.0 - 7.5.0.8 IBM MQ 8.0.0.0 - 8.0.0.7 IBM MQ (LTS) 9.0.0.0 - 9.0.0.1 IBM MQ (CD) 9.0.1.0 - 9.0.3.0 REMEDIATION/FIXES
 

Product VRMF APAR Remediation / First Fix IBM WebSphere MQ 7.0.1 IT22526 Customers on extended support should contact IBM support to acquire a fix. IBM WebSphere MQ 7.1 IT22526 IBM WebSphere MQ V7.1.0.9 [http://www-01.ibm.com/support/docview.wss?uid=swg22010694] IBM WebSphere MQ 7.5 IT22526 Interim Fix IT22526 [https://www-945.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/WebSphere+MQ&release=7.5.0.8&platform=All&function=all] IBM MQ 8.0 IT22526 IBM MQ V8.0.0.8 [http://www-01.ibm.com/support/docview.wss?uid=swg24044322] IBM MQ (LTS) 9.0 IT22526 IBM MQ V9.0.0.2 [http://www-01.ibm.com/support/docview.wss?uid=swg24044038] IBM MQ (CD) 9.0.x IT22526 IBM MQ V9.0.4 [http://www-01.ibm.com/support/docview.wss?uid=swg24043348] WORKAROUNDS AND MITIGATIONS
None. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B027

```text
fixlets do not appear in console bigfix
Work with ILTM 9.2.7 / 9.5.4.38. In the bigfix console the fixlets do not appear, under the tree: Sites-> IBM License Reporting (ILTM) v9 -> Fixlets and Task.

Attached image. Do you have any ideas?

Greetings and thank you BigFix
```

答案正文：

```text
Upgrade to version 9.2.7 or later using the following procedure: 

 * In IBM Endpoint Manager console, expand IBM BigFix Inventory or IBM License Reporting (ILMT) node under Sites node in the tree panel. 
 * Click Fixlets and Tasks node. Fixlets and Tasks panel will be displayed on the right. 
 * In the Fixlets and Tasks panel locate Upgrade to the newest version of IBM BigFix Inventory 9.x or Upgrade to the newest version IBM License Metric Tool 9.x fixlet and run it against the computer that hosts your server.

WORKAROUNDS AND MITIGATIONS
None [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Check with the firewall/proxy/IPS/network admin and ask them to check the logs for dropped packets or downloads and to adjust the rules to allow the BES Support site content through. |  |  |
| F2 | Try turning off Internet Explorer Enhanced Security Configuration [https://blogs.technet.microsoft.com/chenley/2011/03/10/how-to-turn-off-internet-explorer-enhanced-security-configuration/] for Administrators to see if this resolves the issue. |  |  |

评审人：________　日期：________　整题判断：________

## B028

```text
Does Tivoli Monitoring NetApp monitoring agent support OCUM environments?
```

答案正文：

```text
*  7.2.0.3-TIV-ITM_NETAPP-IF0001
   http://www-01.ibm.com/support/docview.wss?uid=swg24041828 [http://www-01.ibm.com/support/docview.wss?uid=swg24041828]
   
   
    
   
   

PROBLEM SUMMARY
 *  NetApp agent does not support monitoring of underlying storage
   resources of On-command Unified Manager 6.x.environment (OCUM). [S1]
*  Data provider has been updated to enable it to work with
   OnCommand Unified Manager 6.x environment.
   
   
    
   
   

TEMPORARY FIX
 *  We published NetApp agent 7.2 FP3 IF1 which supports monitoring
   of OCUM 6.x environment.
   You can find below the published link:
   http://www-01.ibm.com/support/docview.wss?uid=swg24041828 [http://www-01.ibm.com/support/docview.wss?uid=swg24041828]
   
   
    
   
   

COMMENTS [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B029

```text
How to import a certificate in ITCAM for Data Power ?
How can I import a certificate in ITCAM for Data Power?
```

答案正文：

```text
Import the certification file into the agent by doing the following command:

Note : You can use either .cer or .pem. 
Make sure the file is in ASCII not binary. 
Where the /usr/ITM/JRE is your Java location and <fileName> is your file name.

ex: 
/usr/ITM/JRE/aix526/jre/bin/keytool -import -trustcacerts -alias 
ligitalsso -keystore /usr/ITM/JRE/aix526/jre/bin/lib/security/cacerts 
-storepass <fileName> -file /NEWSSL-sscert.cer [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Import the certification file into the agent by doing the following command |  |  |
| F2 | You can use either .cer or .pem |  |  |
| F3 | Make sure the file is in ASCII not binary |  |  |

评审人：________　日期：________　整题判断：________

## B030

```text
Why does my upgrade to Portal 8001 CF14 fail with the following errors, ADMA5008E, ADMA0063E, ADMA5069E, WASX7017E?
```

答案正文：

```text
- Shut-down the DMGR
- Clear out the contents of the following directories:

dmgr_profile/wstemp
dmgr_profile/temp

- Restart the DMGR.
- Re-attempt the upgrade




This can also occur when the DMGR is running as a non-root user. If so, please stop and re-start the DMGR as root and attempt the upgrade again. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This exception can happen during ejbdeploy after the WebSphere Application Server has been upgraded, and old OSGI cache remains for the ejbdeploy tool |  |  |
| F2 | The OSGI class of the ejbdeploy tool contains class information within the deploytool folder and can become stale if the content inside deploytool has changed |  |  |

评审人：________　日期：________　整题判断：________

## B031

```text
IID 8.5.7 failed to start due to "Java was started but returned exit code=-805306369"
We have installed new IID 8.5.7 on Windows 7 on VMware. The installation was successed. However, IID failed to launch always. The dialog shows "Java was started but returned exit code=-805306369". The IID log shows BundleStatusException. How do we resolve this?
```

答案正文：

```text
To resolve this issue, complete the following steps: 

 1. Add the -Duser.home=C:/temp JVM property to the Process Designer eclipse.ini file.
    
    
 2. Restart IBM Process Designer.

 

Cross reference information Segment Product Component Platform Version Edition Business Integration IBM Business Process Manager Standard Process Designer Windows 8.5.0.1 Business Integration IBM Business Process Manager Express Process Designer Windows 8.5.0.1 
PRODUCT ALIAS/SYNONYM
 BPM [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B032

```text
Need help accessing my SPSS access code?
I downloaded SPSS GradPack (Standard) 25 6 Months for my Mac. The IBM SPSS Statistics 24 licensing page pops up for me to enter the code. I enter the code provided and then hit next, and it tells me the code is too short to be valid? What code do I use then? I need this resolved fast, my first assignment is due soon. I was only given a 16-digit access code, not a 20-digit?



This dW Answers question is about an IBM document with the Title:
SPSS Student Version and Graduate Pack Resources
```

答案正文：

```text
As a workaround, use the LicenseActivator utility from the Terminal application with Administrator rights while connected to the internet:

1.Open the Terminal.app
2. Browse to the /bin directory of the Statistics 24 installation: 


cd /applications/IBM/SPSS/Statistics/24/SPSSStatistics.app/contents/bin 


3. Enter the following command: 


sudo ./licenseactivator <your authorization code> 

 

whereas <your authorization code> needs to be replaced with the 20-digit authorization code you received for licensing. [S6]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | For installation & licensing issues on Student version and Graduate pack, contact your vendor. |  |  |

评审人：________　日期：________　整题判断：________

## B033

```text
Why the Editor for Messages logon page does not work?
We have Editor for Messages installed on a Windows server. Users are accessing the web UI from a terminal server session that has been replaced recently. Users cannot login anymore from the new environment.

The fails as follows : the Editor for Messages logon page loads but when the user wants to validate their user/password by clicking on the "login" button, nothing occurs.
```

答案正文：

```text
知识库无法回答该问题。
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Editor for Messages supports Microsoft Internet Explorer only |  |  |
| F2 | Mozilla Firefox and Google Chrome are not supported |  |  |
| F3 | IE 6, IE 7, IE 8, IE 9 (compatibility view), IE 10(Compatibility view), IE 11(Compatibility view) |  |  |

评审人：________　日期：________　整题判断：________

## B034

```text
Help with Action required for IIIB V9 and WMB V8 Hypervisor Editions for security vulnerabilities in Red Hat Linux
I need to understand details regarding Action required for IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 for security vulnerabilities in Red Hat Linux. Where can I find this information?
```

答案正文：

```text
IBM Action required for IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 for security vulnerabilities in Red Hat Linux - United States

IIB WMB FLASH (ALERT)

ABSTRACT
 IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 require customer action for security vulnerabilities in Red Hat Linux 

CONTENT
IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 ship with Red Hat Enterprise Linux (RHEL) Server 6.2 which is vulnerable to
CVE-2017-16546 

Remediation: 

IBM strongly recommends that you contact Red Hat to obtain and install fixes for Red Hat Enterprise Linux (RHEL) Server 6.2, as applicable.




Cross reference information Segment Product Component Platform Version Edition Business Integration WebSphere Message Broker Hypervisor Edition Linux 8.0 [S1]
IBM Action required for IBM Integration Bus Hypervisor Edition V9.0 and WebSphere     Message Broker Hypervisor Edition V8.0 for security vulnerabilities in Red Hat Linux - United States

IIB WMB FLASH (ALERT)

ABSTRACT
 IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 require customer action for security vulnerabilities in Red Hat Linux 

CONTENT
IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 ship with Red Hat Enterprise Linux (RHEL) Server 6.2 which is vulnerable to: 
CVE-2018-6405 

Remediation: 

IBM strongly recommends that you contact Red Hat to obtain and install fixes for Red Hat Enterprise Linux (RHEL) Server 6.2, as applicable. [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 ship with versions of Red Hat Enterprise Linux (RHEL) Server that are vulnerable to CVE-2016-8677, CVE-2016-8678 CVE-2016-9298, CVE-2014-9915, CVE-2016-10046, CVE-2016-10047, CVE-2016-10048, CVE-2016-10049, CVE-2016-10050, CVE-2016-10051, CVE-2016-10052, CVE-2016-10053, CVE-2016-10054, CVE-2016-10055, CVE-2016-10056, CVE-2016-10057, CVE-2016-10058, CVE-2016-10059, CVE-2016-10060, CVE-2016-10061, CVE-2016-10062, CVE-2016-10063, CVE-2016-10064, CVE-2016-10065, CVE-2016-10066, CVE-2016-10067, CVE-2016-10068, CVE-2016-10069, CVE-2016-10070, CVE-2016-10071, CVE-2016-10144, CVE-2016-10145, CVE-2016-10146, CVE-2017-5506, CVE-2017-5507, CVE-2017-5508, CVE-2017-5511, CVE-2017-6498, CVE-2017-6499, CVE-2017-6500, CVE-2017-6501, CVE-2017-6502, CVE-2016-10252 and CVE-2017-6497 |  |  |
| F2 | IBM Integration Bus Hypervisor Edition V9.0 and WebSphere Message Broker Hypervisor Edition V8.0 ship with Red Hat Enterprise Linux (RHEL) Server 6.2. |  |  |

评审人：________　日期：________　整题判断：________

## B035

```text
Help with Security Bulletin: Vulnerability in Diffie-Hellman ciphers affects IBM Image Construction and CompositionTool. (CVE-2015-4000)
I need to understand details regarding "Security Bulletin: Vulnerability in Diffie-Hellman ciphers affects IBM Image Construction and CompositionTool. (CVE-2015-4000". Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2015-4000 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-4000]
DESCRIPTION: The TLS protocol could allow a remote attacker to obtain sensitive information, caused by the failure to properly convey a DHE_EXPORT ciphersuite choice. An attacker could exploit this vulnerability using man-in-the-middle techniques to force a downgrade to 512-bit export-grade cipher. Successful exploitation could allow an attacker to recover the session key as well as modify the contents of the traffic. This vulnerability is commonly referred to as "Logjam".
CVSS Base Score: 4.3
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/103294 [https://exchange.xforce.ibmcloud.com/vulnerabilities/103294] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:M/Au:N/C:P/I:N/A:N)

AFFECTED PRODUCTS AND VERSIONS
IBM Image Construction and Composition Tool v2.2.1.3 
IBM Image Construction and Composition Tool v2.3.1.0 
IBM Image Construction and Composition Tool v2.3.2.0

REMEDIATION/FIXES
The solution is to apply the following IBM Image Construction and Composition Tool version fixes.

Upgrade the IBM Image Construction and Composition Tool to the following fix levels:

· For IBM Image Construction and Composition Tool v2.2.1.3
· IBM Image Construction and Composition Tool v2.2.1.3 Build 32

http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=1.1.0.5&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.2.1.3-32&includeSupersedes=0 [http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=1.1.0.5&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.2.1.3-32&includeSupersedes=0]


· For IBM Image Construction and Composition Tool v2.3.1.0
· IBM Image Construction and Composition Tool v2.3.1.0 Build 43

http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.0.0.1&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.3.1.0-43&includeSupersedes=0 [http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.0.0.1&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.3.1.0-43&includeSupersedes=0]


· For IBM Image Construction and Composition Tool v2.3.2.0
· IBM Image Construction and Composition Tool v2.3.2.0 Build 16

http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.1.0.0&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.3.2.0-16&includeSupersedes=0 [http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.1.0.0&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.3.2.0-16&includeSupersedes=0]


You should verify applying this configuration change does not cause any compatibility issues. If you change the default setting after applying the fix, you will expose yourself to the attack described above. IBM recommends that you review your entire environment to identify other areas where you have enabled the Diffie-Hellman key-exchange protocol used in TLS and take appropriate mitigation and remediation actions.

WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The TLS protocol could allow a remote attacker to obtain sensitive information, caused by the failure to properly convey a DHE_EXPORT ciphersuite choice |  |  |
| F2 | An attacker could exploit this vulnerability using man-in-the-middle techniques to force a downgrade to 512-bit export-grade cipher |  |  |
| F3 | commonly referred to as "Logjam" |  |  |
| F4 | CVSS Base Score: 4.3 |  |  |
| F5 | (AV:N/AC:M/Au:N/C:P/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B036

```text
Why is the OUTPUT_TYPE specified in the properties file for the custom scripting feature ignored?
Why is the OUTPUT_TYPE specified in the properties file for the custom scripting feature ignored in ITM V6?

Specifying "I" for INTEGER, or "F" for FLOAT for the OUTPUT_TYPE doesn't work, but specifying OUTPUT_TYPE=S results in STRING type for the first token.
```

答案正文：

```text
- TOKEN_TYPES (STRING|INTEGER|FLOAT - Optional).
It defines the output type of additional tokens after the first one. The user can define a maximum of 5 strings, 5 integers and 5 floats. It is a list of types separated by commas:
<token_type>,<token_type>,…
token_type can be empty or one from (case insensitive):
- STRING or S
- INTEGER or I
- FLOAT or F
If <token_type> is empty, the corresponding token is skipped.
Examples of the same valid layouts:
- TOKEN_TYPES=S,I,S,,,F,,F,F
- TOKEN_TYPES=String,integer,S,,,Float,,f,FLOAT

- TOKEN_LABELS (STRING - maximum 16 characters each label - Optional). 
It defines the labels of the tokens defined in TOKEN_TYPES. This value is a list of token labels separated
by commas, and must correspond to the tokens defined by TOKEN_TYPES. 
e.g.:
- TOKEN_TYPES=S,I,S,,,F,,F,F
- TOKEN_LABELS=Cpu Name,Cpu number,Description,,,value 1,,value 2,value 3 
It is ignored if TOKEN_TYPES is not set.

- TOKEN_SEPARATOR (Optional - default semicolon ";"). 
It sets the string to be used as separator to split the output row in tokens. It is ignored if TOKEN_TYPES is not set. Empty value (blank) is accepted as separator and multiple consecutive blanks in output rows are considered as a single one. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | OUTPUT_TYPE (STRING\|INTEGER\|FLOAT - Optional - default string). |  |  |
| F2 | It defines the type of the first token returned by each row of the script; |  |  |

评审人：________　日期：________　整题判断：________

## B037

```text
How to start PC DMgr as a Windows service?
hi all. I just installed BPM 8.5.0.1 Process Center on a Windows 2008 R2 cloud server. The default BPM85 typical installation installs ProcessCenter Quickstart web page for starting the Dmgr and NodeMgr servers using the installation admin user . However, logout stops the services started by and attached to the admin user. I need to have this ProcessCenter (and Deployment Env Process SErvers) BPM85 DMgr / Node/ WASND started as a managed Windows managed service. I didn't see a Service Definition page to select run as Windows service. Can I possibly run BPMConfig -start dmgrprofile as a Windows service or is a profile update to my dmgr (hope not) needed to do this?
```

答案正文：

```text
IBM Specifying the profile path in the BPMConfig properties file for IBM Business Process Manager (BPM) - United States

BPMConfig; profile; path; directory TECHNOTE (FAQ)

QUESTION
 How do you specify the profile path in the configuration properties file for IBM Business Process Manager so you can use it with the BPMConfig command? 

ANSWER [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Place the WASServiceCmd.exe utility in the following directory: install_root\bin |  |  |
| F2 | Launch the command from the command line |  |  |
| F3 | The WASServiceCmd utility prompts you to select specific options and settings from a list and then calls the WASService.exe command passing all selected parameters |  |  |

评审人：________　日期：________　整题判断：________

## B038

```text
Help with Security Bulletin: The WebAdmin context for WMB V8 allows directory listings (CVE-2016-6080)
I need to understand details regarding Security Bulletin: The WebAdmin context for WebSphere Message Broker Version 8 allows directory listings (CVE-2016-6080). Where can I find this information?
  0
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2016-6080 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-6080]
DESCRIPTION: The WebAdmin context for WebSphere Message Broker allows directory listings, which could disclose sensitive information to the attacker.
CVSS Base Score: 5.3
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/117560 [https://exchange.xforce.ibmcloud.com/vulnerabilities/117560] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N) 

AFFECTED PRODUCTS AND VERSIONS
WebSphere Message Broker V8

REMEDIATION/FIXES
 

Product VRMF APAR Remediation/Fix WebSphere Message Broker V8 IT16698 The APAR is available in Fix Pack 8.0.0.8
https://www-304.ibm.com/support/docview.wss?uid=swg24042925 [https://www-304.ibm.com/support/docview.wss?uid=swg24042925] 

For unsupported versions of the product, IBM recommends upgrading to a fixed, supported version/release/platform of the product. 
The planned maintenance release dates for WebSphere Message Broker and IBM Integration Bus are available at : 
http://www.ibm.com/support/docview.wss?uid=swg27006308 [http://www.ibm.com/support/docview.wss?uid=swg27006308]

WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The WebAdmin context for WebSphere Message Broker allows directory listings, which could disclose sensitive information to the attacker |  |  |
| F2 | CVSS Base Score: 5.3 |  |  |
| F3 | (CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B039

```text
How can I obtain a Java thread dump against an execution group in IIB v10?
This Q&A is abstracted from a PMR

How can I obtain a Java thread dump against an execution group in IIB v10?
```

答案正文：

```text
RESOLVING THE PROBLEM


JAVACORE DUMP INSTRUCTIONS

New javacore dump commands have been made available from IIB v10.0.0.9, onwards. 
- The new procedure uses the mqsichangeproperties command. 
- The old procedure uses a custom message flow, and is only applicable for operating systems that use the IBM JRE. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Use command on IIB v10.0.0.9+: mqsichangeproperties <Int.Node> -e <Int.Server> -o ComIbmInternalSupportManager/Java/JVM -n dump -v <dump_type> |  |  |

评审人：________　日期：________　整题判断：________

## B040

```text
Help with Security Bulletin: Authentication vulnerability affects IIB V10.0.0.4 onwards (CVE-2016-8918 )
I need to understand details regarding Security Bulletin: Authentication vulnerability affects IBM Integration Bus V10.0.0.4 onwards (CVE-2016-8918 ). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2016-8918 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-8918]
DESCRIPTION: In non-default configurations, IBM Integration Bus could allow a remote user to authenticate without providing valid credentials.
CVSS Base Score: 5.9
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/118528 [https://exchange.xforce.ibmcloud.com/vulnerabilities/118528] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:N) 

AFFECTED PRODUCTS AND VERSIONS
IBM Integration Bus V10

REMEDIATION/FIXES
 

Product VRMF APAR Remediation/Fix IBM Integration Bus V10 IT15920 The APAR is available in Fix Pack 10.0.0.7 
https://www-304.ibm.com/support/docview.wss?uid=swg24043068 [https://www-304.ibm.com/support/docview.wss?uid=swg24043068] 

For unsupported versions of the product, IBM recommends upgrading to a fixed, supported version/release/platform of the product. 
The planned maintenance release dates for WebSphere Message Broker and IBM Integration Bus are available at : 
http://www.ibm.com/support/docview.wss?uid=swg27006308 [http://www.ibm.com/support/docview.wss?uid=swg27006308]

WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | In non-default configurations, IBM Integration Bus could allow a remote user to authenticate without providing valid credentials |  |  |
| F2 | CVSS Base Score: 5.9 |  |  |
| F3 | CVSS Vector: (CVSS:3.0/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B041

```text
Does IBM DataPower Gateway Appliance support the HTTP CONNECT method?
```

答案正文：

```text
知识库无法回答该问题。
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | an XML Firewall when configuring in the HTTP Options tab, where the user can configure the Proxy Host and Port |  |  |
| F2 | a Multi-Protocol Gateway when configuring an HTTP Proxy Policy in the User Agent |  |  |
| F3 | SSL Proxy requests will work using the CONNECT method for SSL Tunneling when using a Multi-Protocol Gateway when configuring in a User Agent's HTTP Proxy Policy |  |  |
| F4 | The XML Firewall service is not designed to use the CONNECT method for SSL Tunneling |  |  |

评审人：________　日期：________　整题判断：________

## B042

```text
Help with Security Bulletin: WMB and IIB are affected by denial of service vulnerability (CVE-2014-8901)
I need to understand details regarding Security Bulletin: WebSphere Message Broker and IBM Integration Bus are affected by denial of service vulnerability (CVE-2014-8901). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2014-8901 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-8901]
DESCRIPTION: IBM XML4J and XML4C libraries contain a denial of service vulnerability when loading specially crafted content. This causes the CPU to consume 100% of available resources and creates serious performance degradation to the system.
CVSS Base Score: 4
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/99110 [https://exchange.xforce.ibmcloud.com/vulnerabilities/99110] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:L/Au:S/C:N/I:N/A:P) 

AFFECTED PRODUCTS AND VERSIONS
WebSphere Message Broker V8 

IBM Integration Bus V9 and V10 

REMEDIATION/FIXES
 

Product VRMF APAR Remediation/Fix IBM Integration Bus V10 IT07064 An interim fix is available from IBM Fix Central for all platforms.
http://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/Integration+Bus&release=All&platform=All&function=aparId&apars=IT07064 [http://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/Integration+Bus&release=All&platform=All&function=aparId&apars=IT07064]

The APAR is targeted to be available in fix pack 10.0.0.4 IBM Integration Bus V9 IT07064 An interim fix is available from IBM Fix Central for all platforms.
http://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/Integration+Bus&release=All&platform=All&function=aparId&apars=IT07064 [http://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/Integration+Bus&release=All&platform=All&function=aparId&apars=IT07064]

The APAR is targeted to be available in fix pack 9.0.0.6 WebSphere Message Broker
V8
IT07064 An interim fix is available from IBM Fix Central for all platforms.
http://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/WebSphere+Message+Broker&release=All&platform=All&function=aparId&apars=IT07064 [http://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/WebSphere+Message+Broker&release=All&platform=All&function=aparId&apars=IT07064] 

The APAR is targeted to be available in fix pack 8.0.0.7 
To mitigate the vulnerability, after an interim fix or fixpack containing IT07064 is applied you must set the following environment variable to disable the use of regular expressions by the MRM parser before starting the broker or integration node: 


 * MQSI_DISABLE_REGEX_IN_XML4C=yes 



For unsupported versions of the product IBM recommends upgrading to a fixed, supported version/release/platform of the product.  

The planned maintenance release dates for WebSphere Message Broker and IBM Integration Bus are available at : 
http://www.ibm.com/support/docview.wss?uid=swg27006308 [http://www.ibm.com/support/docview.wss?uid=swg27006308]

WORKAROUNDS AND MITIGATIONS
None known [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM XML4J and XML4C libraries contain a denial of service vulnerability when loading specially crafted content, causing CPU to consume 100% resources |  |  |
| F2 | CVSS Base Score: 4 |  |  |
| F3 | CVSS Vector: (AV:N/AC:L/Au:S/C:N/I:N/A:P) |  |  |

评审人：________　日期：________　整题判断：________

## B043

```text
My SystemOut.log is overfilled by messages SECJ0371W (LTPA token expired). I am sick and tired of them. Can I disable them?
```

答案正文：

```text
customers to unexpected conditions. For instance a client
   continues to send an expired token repeatedly.
   The customer is requesting the ability to disable the logging
   of the SECJ0371W message. [S1]
*  A security custom property will be used to disable the logging
   of the SECJ0371W message. Setting this property to true will
   disable future logging of the message.
   com.ibm.websphere.security.ltpa.disableSECJ0371W=true
   
   The fix for this APAR is currently targeted for inclusion in
   fix packs 8.0.0.13 and 8.5.5.10.  Please refer to the
   Recommended Updates page for delivery information:
   http://www.ibm.com/support/docview.wss?rs=180&uid=swg27004980 [http://www.ibm.com/support/docview.wss?rs=180&uid=swg27004980]
   
   
    
   
   

TEMPORARY FIX

COMMENTS [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | A security custom property will be used to disable the logging of the SECJ0371W message |  |  |
| F2 | com.ibm.websphere.security.ltpa.disableSECJ0371W=true |  |  |

评审人：________　日期：________　整题判断：________

## B044

```text
Help with Security Bulletin: Vulnerabilities in IBM Dojo Toolkit affect IBM Image Construction and Composition Tool (CVE-2014-8917)
I need to understand details regarding "Security Bulletin: Vulnerabilities in IBM Dojo Toolkit affect IBM Image Construction and Composition Tool (CVE-2014-8917)". Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2014-8917 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-8917]

DESCRIPTION: IBM Dojo Toolkit is vulnerable to cross-site scripting, caused by improper validation of user-supplied input.

CVSS Base Score: 4.3
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/99303 [https://exchange.xforce.ibmcloud.com/vulnerabilities/99303] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:M/Au:N/C:N/I:P/A:N)

AFFECTED PRODUCTS AND VERSIONS
IBM Image Construction and Composition Tool v2.2.1.3 
IBM Image Construction and Composition Tool v2.3.1.0 
IBM Image Construction and Composition Tool v2.3.2.0

REMEDIATION/FIXES
The solution is to apply the following IBM Image Construction and Composition Tool version fixes.

Upgrade the IBM Image Construction and Composition Tool to the following fix levels or higher: 


For IBM Image Construction and Composition Tool v2.2.1.3  * 
 * 
 * 
 * 
 * http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=1.1.0.5&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.2.1.3-28&includeSupersedes=0


For IBM Image Construction and Composition Tool v2.3.1.0  * 
 * 
 * 
 * 
 * http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.0.0.1&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.3.1.0-38&includeSupersedes=0


For IBM Image Construction and Composition Tool v2.3.2.0  * 
 * 
 * 
 * http://www-933.ibm.com/support/fixcentral/swg/selectFixes?parent=PureSystems&product=ibm/WebSphere/PureApplication+System&release=2.1.0.0&platform=All&function=fixId&fixids=ICCT_efix_Repository_2.3.2.0-12&includeSupersedes=0

WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM Dojo Toolkit is vulnerable to cross-site scripting, caused by improper validation of user-supplied input |  |  |
| F2 | CVSS Base Score: 4.3 |  |  |
| F3 | CVSS Vector: (AV:N/AC:M/Au:N/C:N/I:P/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B045

```text
Why are some Datatypes corrupt after Impact cluster failover/failback ?
Running Impact 7.1.0.11. The symptom is whenever Impact does a failover, a couple DataTypes
turn out empty.

I've checked the type files before and after Impact failover and the difference happens in the property

*.SQL.USERPARAMETERS

This property no longer exists for the corrupted datatypes".
```

答案正文：

```text
*  Work- around ...
   
   set impact.cluster.readlimit to 32768 at least.
   
   Update <SERVERNAME>_server.props files both
   on Primary and Backup and
   restart the server.
   You might have to delete the corrupt property files
   
   for the Backup to grab the new ones from the Primary.
   
   
    
   
   

PROBLEM SUMMARY
 *  TBSM 6.1 Failover system fails to restart.
   configuratrion files were corrupted in
    /opt/IBM/tivol/tbsm/etc [S6]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Add the property to $NCHOME/impact/etc/<SERVERNAME>_server.props file where size limit can be 8192, 16384, 32768, etc.. |  |  |
| F2 | The property would have to be added to all ImpactServers in the Cluster and would require a restart to enable |  |  |
| F3 | ensure that there are no trailing white-space characters on the property |  |  |
| F4 | The APAR is not an issue in Impact 6 and 7, but one would still have to include this property with an appropriate value |  |  |
| F5 | The character length includes the whole USERPARAMETERS property name as well as the definition |  |  |

评审人：________　日期：________　整题判断：________

## B046

```text
How to fix the DB2 errors in Portal ?
How could we fix the below DB2 errors in WebSphere Portal:

DB2 SQL Error: SQLCODE=-551, SQLSTATE=42501, SQLERRMC=WPUSER;SELECT;JCR.SHORTCUT_SEQ, DRIVER=4.15.113

DB2 SQL Error: SQLCODE=-727, SQLSTATE=56098, SQLERRMC=2;-551;42501;WPUSER|SELECT|JCR.SHORTCUT_SEQ, DRIVER=4.15.113
```

答案正文：

```text
RESOLVING THE PROBLEM
Have the DBA correct the issue and provide the permissions needed. 

The following Portal links can help provide guidance on the proper permissions that Portal expects...

http://www-01.ibm.com/support/knowledgecenter/SSHRKX_8.5.0/mp/eua-workflows/kc-db-setupdb-db2.dita?lang=en [http://www-01.ibm.com/support/knowledgecenter/SSHRKX_8.5.0/mp/eua-workflows/kc-db-setupdb-db2.dita?lang=en]

http://www-01.ibm.com/support/knowledgecenter/SSHRKX_8.5.0/mp/eua-workflows/kc-db-grantpermrun-db2.dita?lang=en [http://www-01.ibm.com/support/knowledgecenter/SSHRKX_8.5.0/mp/eua-workflows/kc-db-grantpermrun-db2.dita?lang=en] [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B047

```text
How to have IBM HTTP Server re-direct an application URL from HTTPS to HTTP?
We have an application which uses SSL, but we need to make this http only. We disabled all the SSL, but many clients URLs are still pointing to https. So we need a HTTP Server redirect to change these URLs from https to http. Is this possible?
```

答案正文：

```text
QUESTION
 How do you configure IIS to redirect http://server/ase [http://server/ase] to https://server/ase [https://server/ase] when accessing the console of IBM Security AppScan Enterprise? 

CAUSE
You change ASE configuration to be accessed through HTTPS instead of HTTP. 

However, your current users still the ASE console through HTTP, and you would like your users still get access without updating the URL. [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | First, make sure the LoadModule line for mod_rewrite is uncommented in the httpd.conf |  |  |
| F2 | LoadModule rewrite_module modules/mod_rewrite.so |  |  |
| F3 | RewriteEngine on |  |  |
| F4 | RewriteRule ^(.*) https://%{SERVER_NAME}%{REQUEST_URI} [R,L] |  |  |
| F5 | Finally, restart the IBM HTTP Server after making the preceding changes |  |  |

评审人：________　日期：________　整题判断：________

## B048

```text
How to define shared libraries for ODM ruleApps on WAS traditional?
What is the proper way to define a shared lib for RuleApps without giving up the isolated mode of the XU resource adapter? Is it "works as designed" that isolating of the XU prevents the resource adapter from seeing shared lib classes from other classloaders?
```

答案正文：

```text
...Use an isolated class loader for this shared library...
... isolatedClassLoader={"true"|"false"} ..


It is possible to set this in the WAS Admin Console when creating a shared library for WAS v7.x/v8.x. 

 * 
 * 
   Shared Libraries > {your shared lib Name}
   //==
   ...
   --------------
   Class Loading
   [x ] Use an isolated class loader for this shared library
   //===
   


As shown in this screenshot: 

[/support/docview.wss?uid=swg21677153&aid=1] [/support/docview.wss?uid=swg21677153&aid=1] 

How can this be done for an Enhanced EAR deployment in the RAD 8.0.4.x? 
ANSWER
The Admin Console Shared Libraries: Class Loading setting
[ ] Use an isolated class loader for this shared library
has never been part of the Enhanced EAR editor deployment Shared Library settings in RAD v8.0.x and earlier. The editor uses/sets the following files for a shared library in the EAR folder<workspace>\TestEAR\META-INF\ibmconfig\ :


..\cells\defaultCell\applications\defaultApp\deployments\defaultApp\deployment.xml
and 
..\cells\defaultCell\nodes\defaultNode\servers\defaultServer\libraries.xml


The support for the isolated classloader for shared library setting was added in RAD 8.5.1 to the WAS "Deployment" editor:


//== {Add|Edit} Library Entry
...
..
--- Classpath Loading ---------------------------------
[ ] Use an isolated classloader for this shared library
-------------------------------------------------------
//== [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | In order to support the existence of multiple versions of the driver jars, the "Isolate this resource provider" configuration helps to ensure there are no conflicts. |  |  |
| F2 | This needs to be configured on each JDBC Provider. |  |  |
| F3 | In this scenario, the resource provider classes from different versions of the jars are not imported or accessed to verify if the isolation has indeed worked. |  |  |
| F4 | Go to the JDBC Provider and enable "isolate the resource provider". |  |  |
| F5 | When "Isolate this resource provider" is enabled, it ensures that only the jar that was specified in the classpath will be used for all the datasources under that particular JDBC provider. |  |  |

评审人：________　日期：________　整题判断：________

## B049

```text
Deploying RuleRunner on a separate server
Hello everyone,

I am trying to have a setup as follows:

Server 1: Running Full Datacap Features
Server 2: Running only the RuleRunner service

I managed to deploy Server 1 successfully and all modules are working.

On Server 2, I installed the following:
Datacap Client, Rulerunner, and connectors

I updated the Application Manager on server 2 to point to \\server1\Datacap\datacap.xml

I can successfully open that path from Server 2 using internet explorer.

When I try to open any application such as TravelDocs using Datacap Deskstop from server 2, I receive the following error:

Unable to connect to Datacap application TravelDocs.

Any hints as to what the issue might be ?

Regards
```

答案正文：

```text
* In Application Manager, verify that the server information on the Taskmaster tab is correct. 
 * In Application Manager, verify that the Service tab points to the correct datacap.xml file and that the file correctly points from there to the application folder. 
 * When starting Rulerunner, verify that Application Manager and Datacap Studio are either not running or specifically in a state that does not lock any files. 
 * If not specified, Rulerunner will attempt to connect through both IPv4 and IPv6. The error will be generated in the log when the unused protocol is tried. For this situation, the error can be ignored. However, the protocol can be set through the Taskmaster tab in Application Manager to eliminate this cause of the error. 
 * Verify that the Rulerunner service is running under an account that has at least read permissions to the application folder. 
 * With multiple threads all attempting to establish connections, some attempts may fail because the server is momentarily busy processing another request. Verify that in the app file, tmservers section, all servers have retry="3". [S7]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B050

```text
How can I export a private key from DataPower Gateway Appliance?
Is it possible to export a private key from DataPower Gateway Appliance?
```

答案正文：

```text
Question: Can the HSM device store certificates? 

Answer: No. The HSM device only stores private keys.

Question: Can I export private keys from the HSM device?
Answer: Yes. Private keys can be exported from the HSM device using the crypto-export command and imported into another HSM device using the crypto-import command as long as the hardware platforms are compatible. 9235 appliances with HSM are compatible with each other in terms of exported HSM keys. 7198 and 7199 appliances with HSM are compatible with each other in terms of exported HSM keys. HSM keys cannot be exported from a 9235 appliance and imported into a 7198/7199 appliance or vice-versa. [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | HSM-enabled DataPower appliances support the export of private keys using the crypto-export command |  |  |
| F2 | HSMs must be initialized and in the same key sharing domain on exporting and importing machines |  |  |
| F3 | The private key in question must be marked exportable at keygen time (see keygen's exportable option) |  |  |
| F4 | HSMs on exporting and importing machines must share internal key-wrapping keys (see hsm-clone-kwk command) |  |  |

评审人：________　日期：________　整题判断：________

## B051

```text
Why am I getting StaleConnectionException on WebSphere side while Oracle is throwing 'OALL8 is in an inconsistent state'?
In the WebSphere Application Server SystemOut.log file we see this message:

ConnectionEve A J2CA0056I: TheConnection Manager received a fatal connection error from the Resource Adapter for resource jdbc/<data source name>. The exception which was received is com.ibm.websphere.ce.cm.StaleConnectionException: OALL8 is in an inconsistent state:java.sql.SQLException: OALL8 is in an inconsistent state.
How can this be resolved?
```

答案正文：

```text
IBM WebSphere Portal SystemOut.log J2CA0056I com.ibm.websphere.ce.cm.StaleConnectionException Connection reset - United States

com.ibm.websphere.ce.cm.StaleConnectionException; connection reset; Purge Policy; purge; policy; EntirePool; entire pool; Minimum Connections; minimum; connections; Unused Timeout; unused; timeout; time out; firewall; data source; connection pool settings; connection pool; connection; pool; settings; staleconnection; stale connection; exception; reset TECHNOTE (TROUBLESHOOTING)

PROBLEM(ABSTRACT)
 This technote describes a solution for IBM WebSphere Portal SystemOut.log entry, "J2CA0056I com.ibm.websphere.ce.cm.StaleConnectionException Connection reset" error. 

SYMPTOM
The WebSphere Portal SystemOut.log shows: 

[datetime] 0000008b ConnectionEve A J2CA0056I: The Connection Manager received a fatal connection error from the Resource Adapter for resource jdbc/customdb. The exception which was received is com.ibm.websphere.ce.cm.StaleConnectionException: [ibm][db2][jcc][t4][2030][11211] A communication error has been detected. Communication protocol being used: TCP/IP.
Communication API being used: SOCKETS. Location where the error was detected: T4Agent.sendRequest().
Communication function detecting the error: OutputStream.flush(). Protocol specific error codes Connection reset, *, 0. Message: Connection reset:com.ibm.db2.jcc.c.DisconnectException: [ibm][db2][jcc][t4][2030][11211] A communication error has been detected. Communication protocol being used: TCP/IP.
Communication API being used: SOCKETS. Location where the error was detected: T4Agent.sendRequest().
Communication function detecting the error: OutputStream.flush(). Protocol specific error codes Connection reset, *, 0. Message: Connection reset:java.net.SocketException: Connection reset [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B052

```text
How can I get a new authorization code for my new computer?
I purchased a new computer and would like to install spss 18 on it. I have the gradpack. However, the authorization code failed when I attempted to install the software on my new machine.
```

答案正文：

```text
2. License the software on the new host machine/computer. 
 * If you have authorization code for the product, you may use this authorization code. 
 * If you are using a pre-existing authorization code and receive a 'You are not allowed to generate any more new licenses' message, instructions for resolving this issue can be found here. [http://www.ibm.com/support/docview.wss?uid=swg21480566] 
 * If you do not have an authorization code for the product, instructions for creating an authorization code can be found here. [http://www-01.ibm.com/support/docview.wss?uid=swg21980065] 
 * If you have more than one authorization code available to you, instructions for confirming the authorization code can be found make sure you are here [http://www.ibm.com/support/docview.wss?uid=swg21486143]. 

Complete! 

You should now be able to run your software. [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B053

```text
MQSeries Events correlation
How are MQSeries Events cleared?
```

答案正文：

```text
ANSWER
The MQSeries Events workspace displays data from the Current Events attribute group. Since this data is stored in memory, stopping and restarting the MQ Monitoring agent will clear all the data in the Current Events table. [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The MQSeries Events workspace displays data from the Current Events attribute group |  |  |
| F2 | Since this data is stored in memory, stopping and restarting the MQ Monitoring agent will clear all the data in the Current Events table |  |  |

评审人：________　日期：________　整题判断：________

## B054

```text
i cannot enter SPSS statistics trial program
I've downloaded the 14-days trial of SPSS subscription for 32bit, windows. After opening the program I'm asked to login and after entering my username and password a blank page comes up. And there is no way to proceed from here. I already saw previous answers about SPSS trial Login error, and there is a link(https://ibm.box.com/s/huaafbjzabkyblh47n7g4l0o4gxp4zdy) to download the zip file of 'jxbrowser'. But i cannot enter the link, and the webpage says "probably the address was changed or deleted."

i'm using Windows 7(32bit), and just want to know how can i resolve it.
```

答案正文：

```text
IBM SPSS Statistics Trial FAQ

Q. I have downloaded and installed Statistics Trial. When I start the product I get a big white box and then nothing else happens. How can I resolve this?
A. This issue is specific to Windows and is most likely caused by installing the 32-bit version of Statistics on a 64-bit machine. To correct the problem, please uninstall the 32-bit, and download an install the 64 bit version of Statistics. 

Q. I have downloaded and installed the Statistics Trial, but when I attempt to start I receive the message: 

 * 
 * https://spsslicensing.mybluemix.net
 * [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The most likely cause of this issue is installation of the 32bit IBM SPSS Statistics Subscription software on a 64bit machine. |  |  |
| F2 | To fix the issue, please uninstall the 32bit and download and install the 64bit application from your Products & Services window on IBM.com. |  |  |
| F3 | If you find that this does not resolve your issue, you have a new issue. |  |  |
| F4 | Please open a Service Request using the Client Support Portal: http://ibm.biz/IBMClientSuccessPortal |  |  |

评审人：________　日期：________　整题判断：________

## B055

```text
Is WAS TE v7.0.0.41 available for RAD?
Is WebSphere Application Server 7.0 Test Environment Extension (WTE) v 7.0.0.41 available for Rational Application Developer for WebSphere Software (RAD) ?
```

答案正文：

```text
If the installation of RAD version 7.x completes except for the WebSphere® Test Environment (WTE) version 6.x server, the IBM Rational Software Development Platform (SDP) will still run, however, WebSphere Application Server (WAS) v6.x Integrated Test Environment may not be available.
Here is a list of things to CHECK first and then re-install if your install completed without installing the WTE. 
A complete set of WTE V6 MANUAL INSTALL instructions also follows, to help you isolate the problem if required. [S1]
File name RAD_V7.0_Part_5.zip
    488MB
    
    IBM Rational Application Developer V7.0 Multiplatform Multilingual Part 9(C96GZML)
    File name RAD_V7.0_Part_9.zip
    531MB
    
    Check the md5 value provide with each zip after downloading any RAD v7.0 zip from PPA.
    
 4. Manually Clean up the WTE/WAS version 6 install before retrying (It might not be necessary to uninstall and reinstall RAD): 
     * Uninstall WebSphere Application Server (WAS) version 6, if it is still installed. You can uninstall it by either of these methods:
       
       Run the IBM Installation Manager (IM) at the command prompt or use Windows Explorer on the icon for uninstall.exe
       <install_dir>\eclipse\launcher.exe
       
       Using: Modify Packages , proceed through the [Next] screens till you get to Features [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This download includes the following update to the WebSphere Application Server v7.0 Test Environment extension included with Rational Software Delivery Platform products |  |  |
| F2 | IBM WebSphere Application Server Version 7 Fix Pack 41 also known as version 7.0.0.41 |  |  |

评审人：________　日期：________　整题判断：________

## B056

```text
Recurrent RES StaleConnectionException
How to prevent rule execution failing because of recurrent StaleConnectionException on ODM 8.8 Rule Execution Server?
```

答案正文：

```text
Configure the WebSphere Application Server data source connection pool [http://publib.boulder.ibm.com/infocenter/wasinfo/v7r0/index.jsp?topic=/com.ibm.websphere.nd.multiplatform.doc/info/ae/ae/udat_conpoolset.html] so as to eliminate occurrences of StaleConnectionException : 

 * Set the Minimum connections to 0 to avoid situations where a connection is kept in the pool to meet the minimum requirement, even though it may have been idle for longer than Unused timeout 
 * Set the values for Unused timeout and Reap timeout so that the sum does not exceed any network level idle connection timeout [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Configure the WebSphere Application Server data source connection pool so as to eliminate occurrences of StaleConnectionException |  |  |
| F2 | Set the Minimum connections to 0 to avoid situations where a connection is kept in the pool to meet the minimum requirement, even though it may have been idle for longer than Unused timeout |  |  |
| F3 | Set the values for Unused timeout and Reap timeout so that the sum does not exceed any network level idle connection timeout |  |  |

评审人：________　日期：________　整题判断：________

## B057

```text
Help with Security Bulletin: IBM WebSphere MQ is affected by a vulnerability in GSKit (CVE-2014-0076)
I need to understand details regarding Security Bulletin: IBM WebSphere MQ is affected by a vulnerability in GSKit (CVE-2014-0076). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVE-ID: CVE-2014-0076 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-0076]
DESCRIPTION: An attacker running a program on the same machine as where the victim is running a program could use CPU timing information to discover key information about certain kinds of binary type Elliptic Curves used in Digital signatures during signing operations. Although GSKit only generates Prime type Elliptic Curves, externally generated keys may be imported in GSKit.
From WebSphere MQ version 7.1, GSKit version 8.0 is integrated with WebSphere MQ. For WebSphere MQ 7.0.1, GSKit version 7 or version 8 was installed separately.

CVSS Base Score: 2.1
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/91990 [https://exchange.xforce.ibmcloud.com/vulnerabilities/91990]
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:L/AC:L/Au:N/C:P/I:N/A:N)

AFFECTED PRODUCTS AND VERSIONS
IBM WebSphere MQ 8.0, including all maintenance levels. 

IBM WebSphere MQ 7.5, including all maintenance levels. 

IBM WebSphere MQ 7.1, including all maintenance levels. 

IBM WebSphere MQ 7.0.1, maintenance levels from 7.0.1.4 onwards, using GSKit version 8.0.

REMEDIATION/FIXES
IBM strongly recommends that Elliptic Curve CipherSpecs are not used. These CipherSpecs have names starting with 'EC'. 

A summary of MQ CipherSpecs and protocols can be found in the IBM Knowledge Center Specifying CipherSpecs [http://www-01.ibm.com/support/knowledgecenter/SSFKSJ_8.0.0/com.ibm.mq.sec.doc/q014260_.htm] topic. [S1]
VULNERABILITY DETAILS
CVE-ID: CVE-2014-0076 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-0076]
内容：
第三者に攻撃により、CPUタイミングなどを利用して、楕円曲線デジタル署名アルゴリズム（ECDSA）のワンタイムトークンを取得される可能性があります。 
WebSphere MQ version 7.1は、GSKit version 8.0, WebSphere MQ 7.0.1は、GSKit version 7 もしくは 8 を提供しています。


CVSS Base Score: 2.1
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/91990 [https://exchange.xforce.ibmcloud.com/vulnerabilities/91990]
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:L/AC:L/Au:N/C:P/I:N/A:N)

AFFECTED PRODUCTS AND VERSIONS
次の製品・バージョンに影響があります。 

IBM WebSphere MQ 8.0 (すべてのレベル) 

IBM WebSphere MQ 7.5 (すべてのレベル) 

IBM WebSphere MQ 7.1 (すべてのレベル) 

IBM WebSphere MQ 7.0.1 (7.0.1.4以降 GSKit verion 8.0 が提供されています)

REMEDIATION/FIXES
対応策：
IBMは、楕円曲線 CipherSpecsの使用を推奨しません。このCipherSpecsは、'EC'で始まるCipherSpecs名です。


MQ で使用できるCipherSpecs は、IBM Knowledge Center CipherSpecsの指定 [http://www-01.ibm.com/support/knowledgecenter/SSFKSJ_8.0.0/com.ibm.mq.sec.doc/q014260_.htm] に記載されています。 [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | An attacker on the same machine could use CPU timing information to discover key information about binary type Elliptic Curves used in Digital signatures |  |  |
| F2 | Although GSKit only generates Prime type Elliptic Curves, externally generated keys may be imported in GSKit |  |  |
| F3 | From WebSphere MQ version 7.1, GSKit version 8.0 is integrated with WebSphere MQ; for WebSphere MQ 7.0.1, GSKit version 7 or version 8 was installed separately |  |  |
| F4 | CVSS Base Score: 2.1 |  |  |
| F5 | CVSS Vector: (AV:L/AC:L/Au:N/C:P/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B058

```text
Why am I getting an SSL Key Exception (RSA premaster secret error) when trying to create a syndication pair?
When trying to create the syndication pair for a virtual portal, I am getting the following exception:

"IWKWC0016E: The remote service can not be retrieved. Either the URL you entered is incorrect, the server you indicated does not contain IBM Web Content Manager or the web service has been incorrectly configured and could not be located. Check the log for more details https://1.23.456.789 <-- your ip address or hostname will be shown here

/wps/wcm/vpname/basicauth/SyndicationServlet?reqlocale=en_US& javax.net.ssl.SSLKeyException: RSA premaster secret error"
```

答案正文：

```text
Check your Credential Vault - the Userid is most likely not an Admin, therefore this issue can be occurring. Change that ID within the credential vault to an Admin ID, and then check for issue. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The default restricted policy file has a 2048 key size limit. |  |  |
| F2 | If the RSA key size exceeds this limit then this error is expected. |  |  |

评审人：________　日期：________　整题判断：________

## B059

```text
Error running krzgrant.sql script provided with 6.3.1.2-TIV-ITM_KRZ-IF0003.tar
When running the krzgrant.sql script provided in the package - 6.3.1.2-TIV-ITM_KRZ-IF0003.tar get the following errors:

ERROR at line 1:
ORA-00942: table or view does not exist ORA-06512: at line 50 

How to correct this?
```

答案正文：

```text
SUBSCRIBE
You can track all active APARs for this component.



APAR STATUS
 * CLOSED AS PROGRAM ERROR.
    
   
   

ERROR DESCRIPTION
 *  ITCAM Extended Agent will occupy the oracle sessions more and
   more if the agent oracle user do not have all authority in the
   krzgrant.sql.
   
   
   This is due to the agent do not disconnect from oracle database
   for the error message of "ORA-00942 Table or View does not
   exist" and try to reconnect to oracle database with a new
   session in each interval.
   
   Detailed Recreation Procedure:
   1. Create an Oracle user and only grant with connect/create
   session privileges, such as 'tivoli'.
   
   2. Do not run the krzgrant.sql for this new Oracle user.
   
   3. Create a new agent instance with this Oracle user and startup
   agent instance.
   
   4. Check the session number owned by this new Oracle user as
   below after agent running for few minutes.
   
   
   SQL> select count(*) from v$session where username='TIVOLI'; [S3]
APAR STATUS
 * CLOSED AS PROGRAM ERROR.
    
   
   

ERROR DESCRIPTION
 *  ITCAM Extended Agent will occupy the oracle sessions more and
   more if the agent oracle user do not have all authority in the
   krzgrant.sql.
   
   
   This is due to the agent do not disconnect from oracle database
   for the error message of "ORA-00942 Table or View does not
   exist" and try to reconnect to oracle database with a new
   session in each interval.
   
   Detailed Recreation Procedure:
   1. Create an Oracle user and only grant with connect/create
   session privileges, such as 'tivoli'.
   
   2. Do not run the krzgrant.sql for this new Oracle user.
   
   3. Create a new agent instance with this Oracle user and startup
   agent instance.
   
   4. Check the session number owned by this new Oracle user as
   below after agent running for few minutes.
   
   
   SQL> select count(*) from v$session where username='TIVOLI';
   
   
    
   
   

LOCAL FIX

PROBLEM SUMMARY
 *  *************************************************************
   * USERS AFFECTED:
   ITCAM Extended Agent for Oracle Database 6.3.1
   *************************************************************
   * PROBLEM DESCRIPTION:
   ITCAM Extended Agent will occupy the oracle sessions more and
   more if the agent oracle user do not have all authority in the
   krzgrant.sql.
   
   
   *************************************************************
   * RECOMMENDATION:
   apply next ifix when available
   *************************************************************
   
   
    
   
   

PROBLEM CONCLUSION
 *  The fix for this APAR is contained in the following packages:
   
   IBM Tivoli Composite Application Manager for Applications:
      Extended Oracle Agent 6.3.1-TIV-ITM_KRZ-IF0002
   
   
    
   
   

TEMPORARY FIX
 *  The temporary fix is to run product provided 'krzgrant.sql' to
   ensure the agent oracle user has all authorities.
   
   
    
   
   

COMMENTS [S4]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Run the krzgrant.sql script |  |  |
| F2 | 6.3.1-TIV-ITM_KRZ-FP0001 |  |  |

评审人：________　日期：________　整题判断：________

## B060

```text
Has ITCAM for J2EE 7.1.1 IF4 been released?
```

答案正文：

```text
The following are the part numbers for the newly GA'd ITCAM for J2EE v7.1.1: 

CN0PIEN ITCAM Agent for J2EE V7.1.1.0, Win, En 

CN0PJEN ITCAM Agent for J2EE V7.1.1.0, AIX, En 

CN0PKEN ITCAM Agent for J2EE V7.1.1.0, Linux, En 

CN0PLEN ITCAM Agent for J2EE V7.1.1.0, pLinux, En 

CN0PMEN ITCAM Agent for J2EE V7.1.1.0, zLinux, En 

CN0PNEN ITCAM Agent for J2EE V7.1.1.0, Solaris, En 

CN0PPEN ITCAM Agent for J2EE V7.1.1.0, HP-UX, En 

CN0PQEN ITCAM Agent for J2EE V7.1.1.0, Support Files

 

PRODUCT ALIAS/SYNONYM
 ITCAM ITCAMfJ2EE [S5]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B061

```text
How to resolve DataPower firmware loading error % Loading firmware failed: Internal receive API error (3)?
Message % Loading firmware failed: Internal receive API error (3) was observed during firmware update. How do you resolve this issue?
```

答案正文：

```text
ERROR DESCRIPTION
 *  When applying an IBM MQ Appliance firmware update, the following
   message will be seen:
   
   Invoking dynamic loader
   % Loading firmware failed: Internal receive API error (3)
   
   The installation may succeed despite this error. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B062

```text
Why do I receive the message, "IKJ79154I INSTALLATION EXIT IKJEESX0 REQUESTED TERMINATION. " for a TSO SEND command?
If you issue the TSO SEND command in a batch job and receive this message:

IKJ79154I INSTALLATION EXIT IKJEESX0 REQUESTED TERMINATION.
IKJ79154I REASON CODE X'00000004'.
```

答案正文：

```text
Code the appropriate security definitions for FEK.CMD.SEND and FEK.CMD.SEND.CLEAR. [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | coded a facility class for the FEK.CMD.SEND and FEK.CMD.SEND.CLEAR |  |  |

评审人：________　日期：________　整题判断：________

## B063

```text
When should I use conversation sharing in DataPower MQ queue managers?
MQ version 7.0 introduced a new feature, conversation sharing. Are there any special values on DataPower when configuring conversation sharing?
```

答案正文：

```text
IBM WebSphere MQ server version 7.0 and later releases provide sharing conversations (SHARECNV) attribute on SVRCONN channel that specifies the maximum number of conversations that can share each TCP/IP channel instance. This feature can be configured in DataPower as it uses client connection with queue manager SVRCONN channel. 
The default setting of sharing conversations (SHARECNV) value is zero in DataPower mq-qm object. The same default value for MQ SVRCONN channel is 10. The sharing conversations value is 
negotiated between MQ server and DataPower and the lower value takes effect. However, in current versions of the DataPower firmware, the sharing conversations setting of 1 is treated as 0 when negotiating with MQ server.

There are three use cases to configure Sharing Conversations in DataPower mq-qm object: 

Case #1 : The negotiated sharing conversations value is 0 - The channel runs in a mode similar to WebSphere MQ V6 and does not uses features such as [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The default setting of sharing conversations (SHARECNV) value is zero in DataPower mq-qm object |  |  |
| F2 | The same default value for MQ SVRCONN channel is 10 |  |  |
| F3 | The sharing conversations value is negotiated between MQ server and DataPower and the lower value takes effect |  |  |
| F4 | in current versions of the DataPower firmware, the sharing conversations setting of 1 is treated as 0 when negotiating with MQ server |  |  |

评审人：________　日期：________　整题判断：________

## B064

```text
Unable to open profile from P8 Content Engine Configuration manager (CMUI) on Redhat Linux 7.2, getting GPF and javacore dump.
Launch configmgr then try to open an existing profile. Once I click ok on the dialog box to
"Verify your application server setting before proceeding..." Configuration manager would crash and GPF. I can see the javacore.txt and dmp file created.
The javacore.txt contains the following:

0SECTION TITLE subcomponent dump routine NULL =============================== 1TICHARSET UTF-8 1TISIGINFO Dump Event "gpf" (00002000) received 1TIDATETIME Date: 2016/05/05 at 04:53:30 1TIFILENAME Javacore filename: /opt/IBM/FileNet/ContentEngine/tools/configure/javacore.20160505.045330.25035.0002.txt 1TIREQFLAGS Request Flags: 0x81 (exclusive+preempt) 1TIPREPSTATE Prep State: 0x100 (trace_disabled) 1TIPREPINFO Exclusive VM access not taken: data may not be consistent across javacore sections NULL ------------------------------------------------------------------------ 0SECTION GPINFO subcomponent dump routine NULL ================================ 2XHOSLEVEL OS Level : Linux 3.10.0-327.13.1.el7.x86_64 2XHCPUS Processors - 3XHCPUARCH Architecture : x86 3XHNUMCPUS How Many : 1 3XHNUMASUP NUMA is either not supported or has been disabled by user NULL
1XHEXCPCODE J9Generic_Signal_Number: 00000004 1XHEXCPCODE Signal_Number: 0000000B 1XHEXCPCODE Error_Value: 00000000 1XHEXCPCODE Signal_Code: 00000080 1XHEXCPCODE Handler1: F72A2E6A 1XHEXCPCODE Handler2: F724D00A 1XHEXCPCODE InaccessibleAddress: 00000000 NULL
1XHEXCPMODULE Module: /lib/libcairo.so.2 1XHEXCPMODULE Module_base_address: D55FC000

This is a Redhat Linux 7.2 environment with Content Platform Engine CPE 5.2.1.4.
```

答案正文：

```text
RESOLVING THE PROBLEM
Install the missing libraries "adwaita-gtk2-theme" (32 and 64 bit) and "adwaita-gtk3-theme" 64 bit. Please contact RedHat to obtain the missing libraries. [S4]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | "adwaita-gtk2-theme" (32 and 64 bit) |  |  |
| F2 | "adwaita-gtk3-theme" 64 bit |  |  |
| F3 | Please contact RedHat to obtain the missing libraries |  |  |

评审人：________　日期：________　整题判断：________

## B065

```text
Improve Performance of Decision Center and Rule Team Server (RTS)
How can I improve the performance of ODM Decision Center and WebSphere ILOG Rule Team Server (RTS)?
```

答案正文：

```text
If the above recommendations do not help, contact IBM support with the following information:  * Environment details including the application server, JDK, database and operating system. 
 * RTS server logs, including FFDC logs if working with WebSphere Application Server. 
 * The typical behavior of RTS users: Are they mostly viewing or editing? Is there a lot of ruleset generation going on simultaneously while editing? 
 * The typical load on RTS, including the number of simultaneous users and number of rulesets being generated [S1]
* Reduce the memory footprint of the ruleset by setting the ruleset property ruleset.bom.enabled [http://publib.boulder.ibm.com/infocenter/dmanager/v7r5/index.jsp?topic=%2Fcom.ibm.dserver.res%2FContent%2FBusiness_Rules%2F_pubskel%2FInfocenter_Primary%2Fps_DS_RES_Console_OH1654.html] to "false [http://publib.boulder.ibm.com/infocenter/dmanager/v7r5/index.jsp?topic=%2Fcom.ibm.dserver.res%2FContent%2FBusiness_Rules%2F_pubskel%2FInfocenter_Primary%2Fps_DS_Rule_Execution_Server1564.html]" to remove support for BOM based serialization. This property is set to "true" by default when extracting rulesets from Rule Team Server (RTS) and Decision Center, and needs to be explicitly set to "false" in order to deactivate it. (You should set it to "true" if you need to generate an Excel report from a Test Suite/Simulation in RTS or Decision Center.) [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B066

```text
Help with Security Bulletin: Multiple vulnerabilities in IBM® Java SDK affect WebSphere Enterprise Service Bus (CVE-2015-2613)
I would like to know details on how vulnerabilities in IBM Java SDK affect Websphere Application Server and in turn, Websphere Enterprise Service Bus product.
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID:CVE-2015-2613 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-2613]
DESCRIPTION:An unspecified vulnerability and Java SE Embedded related to the JCE component could allow a remote attacker to obtain sensitive information.
CVSS Base Score: 5
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/104734 [https://exchange.xforce.ibmcloud.com/vulnerabilities/104734]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:L/Au:N/C:P/I:N/A:N)

CVEID:CVE-2015-2601 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-2601]
DESCRIPTION:An unspecified vulnerability related to the JCE component could allow a remote attacker to obtain sensitive information.
CVSS Base Score: 5
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/104733 [https://exchange.xforce.ibmcloud.com/vulnerabilities/104733]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:L/Au:N/C:P/I:N/A:N)
CVEID:CVE-2015-4749 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-4749]
DESCRIPTION:An unspecified vulnerability related to the JNDI component could allow a remote attacker to cause a denial of service.
CVSS Base Score: 4.3
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/104740 [https://exchange.xforce.ibmcloud.com/vulnerabilities/104740]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:M/Au:N/C:N/I:N/A:P)

CVEID:CVE-2015-2625 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-2625]
DESCRIPTION:An unspecified vulnerability related to the JSSE component could allow a remote attacker to obtain sensitive information.
CVSS Base Score: 2.6
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/104743 [https://exchange.xforce.ibmcloud.com/vulnerabilities/104743]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:H/Au:N/C:P/I:N/A:N)

CVEID:CVE-2015-1931 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-1931]
DESCRIPTION:IBM Java Security Components store plain text data in memory dumps, which could allow a local attacker to obtain information to aid in further attacks against the system.
CVSS Base Score: 2.1
CVSS Temporal Score: Seehttp://xforce.iss.net/xforce/xfdb/102967 [http://xforce.iss.net/xforce/xfdb/102967]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:L/AC:L/Au:N/C:P/I:N/A:N)

AFFECTED PRODUCTS AND VERSIONS
WebSphere Enterprise Service Bus 6.2
WebSphere Enterprise Service Bus 7.0
WebSphere Enterprise Service Bus 7.5

REMEDIATION/FIXES
Please consult the security bulletin Multiple vulnerabilities in IBM® Java SDK affect WebSphere Application Server July 2015 CPU [http://www-01.ibm.com/support/docview.wss?uid=swg21962931] for vulnerability details and information about fixes. [S1]
VULNERABILITY DETAILS
CVEID:CVE-2015-4872 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-4872]
DESCRIPTION:An unspecified vulnerability related to the Security component has no confidentiality impact, partial integrity impact, and no availability impact.
CVSS Base Score: 5
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/107361 [https://exchange.xforce.ibmcloud.com/vulnerabilities/107361]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:L/Au:N/C:N/I:P/A:N) 

CVEID:CVE-2015-4734 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-4734]
DESCRIPTION:An unspecified vulnerability related to the JGSS component could allow a remote attacker to obtain sensitive information.
CVSS Base Score: 5
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/107356 [https://exchange.xforce.ibmcloud.com/vulnerabilities/107356]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (AV:N/AC:L/Au:N/C:P/I:N/A:N) 

CVEID:CVE-2015-5006 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-5006]
DESCRIPTION:IBM Java Security Components could allow an attacker with physical access to the system to obtain sensitive information from the Kerberos Credential Cache.
CVSS Base Score: 4.6
CVSS Temporal Score: Seehttps://exchange.xforce.ibmcloud.com/vulnerabilities/106309 [https://exchange.xforce.ibmcloud.com/vulnerabilities/106309]for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

AFFECTED PRODUCTS AND VERSIONS
WebSphere Enterprise Service Bus 6.2
WebSphere Enterprise Service Bus 7.0
WebSphere Enterprise Service Bus 7.5

REMEDIATION/FIXES
Please consult the security bulletin http://www-01.ibm.com/support/docview.wss?uid=swg21969620 [http://www-01.ibm.com/support/docview.wss?uid=swg21969620] for vulnerability details and information about fixes. [S5]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | An unspecified vulnerability and Java SE Embedded related to the JCE component could allow a remote attacker to obtain sensitive information |  |  |
| F2 | CVSS Base Score: 5 |  |  |
| F3 | (AV:N/AC:L/Au:N/C:P/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B067

```text
Error TASK001X while upgrading Portal 8.0.0.1 to 8.0.0.1 CF14 during import-nodes sub-task
```

答案正文：

```text
Please make the following change in the WAS Admin Console...
Applications > WebSphere enterprise applications >
JavaContentRepository > Target specific application status > Check the
box for the WebSphere_Portal server > Click Enable Auto Start > Save
changes > restart Portal [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Applications > WebSphere enterprise applications > JavaContentRepository |  |  |
| F2 | Target specific application status > Check the box for the WebSphere_Portal server > Click Enable Auto Start |  |  |
| F3 | Save changes > restart Portal |  |  |
| F4 | After making this change please attempt the CF upgrade again |  |  |

评审人：________　日期：________　整题判断：________

## B068

```text
Help with Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808)
I need to understand details regarding Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
For vulnerability details, see the security bulletin Vulnerability in RC4 stream cipher affects IBM DB2 LUW (CVE-2015-2808). [http://www.ibm.com/support/docview.wss?uid=swg21717865]

AFFECTED PRODUCTS AND VERSIONS
 

Principal Product and Version(s) Affected Supporting Product and Version WebSphere Remote Server version V6.2, 6.2.1, 7.0, 7.1, 7.1.1, 7.1.2, 8.5 IBM DB2 Workgroup Server Edition 
V9.5, 9.7, 10.1, 10.5 [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B069

```text
Executing an in-flight task for a deactivated snapshot for WebSphere Lombardi Edition and IBM Business Process Manager (BPM)
Why do in-flight tasks stop after the snapshot has been deactivated? This question pertains to WebSphere Lombardi Edition V7.2 and IBM Business Process Manager V7.5.1.
```

答案正文：

```text
知识库无法回答该问题。
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B070

```text
Can I change the ITCAM J2EE Agent Monitoring Level via the TEPS in version 7.1.1?
In the 7.1 version of the J2EE agent I could use the Agent Configuration to change the Monitoring Level for the agent- https://www.ibm.com/support/knowledgecenter/en/SS3JRN_7.2.0/com.ibm.itcamfapps_ad.doc_72/J2EE_agent_tema_install_guide/step10.html

So how can I change the Monitoring Level in the 7.1.1 agent?
```

答案正文：

```text
ANSWER
The ITCAM Agent for J2EE 7.1.1 Installation and Customization Guide is available in the knowledge center under the ITCAM for Applications 7.2.1.1 section at the following link-
http://www-01.ibm.com/support/knowledgecenter/SS3JRN_7.2.1.1/com.ibm.itcamfapps_ad.doc_7211/j2ee_tema_installguide.html?lang=en [http://www-01.ibm.com/support/knowledgecenter/SS3JRN_7.2.1.1/com.ibm.itcamfapps_ad.doc_7211/j2ee_tema_installguide.html?lang=en] [S1]
ANSWER
The ITCAM Agent for J2EE 7.1.1 User's Guide is available in the Knowledge Center under the ITCAM for Applications 7.2.1.1 section at the following link-
http://www-01.ibm.com/support/knowledgecenter/SS3JRN_7.2.1.1/com.ibm.itcamfapps_ad.doc_7211/itcam_71_j2ee_tema_help/kyj_overview.html?lang=en [http://www-01.ibm.com/support/knowledgecenter/SS3JRN_7.2.1.1/com.ibm.itcamfapps_ad.doc_7211/itcam_71_j2ee_tema_help/kyj_overview.html?lang=en] [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | In the older release of the J2EE agent (v6.2 FP6), there was an option to specify the Monitoring Level, Sampling Rate and other parameters (threshold values, time intervals, etc..) during the configuration phase of the agent itself. |  |  |
| F2 | The default values for the Monitoring Level and the Sampling Rate are L1 and 2% respectively. |  |  |
| F3 | In the $ITM_HOME/config (Unix) dir or %ITM_HOME%\TMAITM6 (Windows), you will find the <hostname>_yj.xml file. |  |  |
| F4 | Save file, restart the agent. |  |  |
| F5 | If you are deploying a new Weblogic application, stop the agent, modify the <hostname>_yj_<wls_instance>.xml file then restart the agent again. |  |  |

评审人：________　日期：________　整题判断：________

## B071

```text
Help with Security Bulletin: MQSISTOP/STARTMSGFLOW commands with unauthorized user succeed affects WMB and IIB (CVE-2015-5011)
I need to understand details regarding Security Bulletin: MQSISTOP/STARTMSGFLOW commands with unauthorized user succeed affects IBM WebSphere Message Broker and IBM Integration Bus (CVE-2015-5011). Where can I find this information?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2015-5011 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2015-5011]
DESCRIPTION: IBM Integration Bus could allow a local user to start and stop a service that they should not have access to.
CVSS Base Score: 4
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/106403 [https://exchange.xforce.ibmcloud.com/vulnerabilities/106403] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N)

AFFECTED PRODUCTS AND VERSIONS
 IBM Integration Bus V9 

 WebSphere Message Broker V8

REMEDIATION/FIXES
 

Product VRMF APAR Remediation/Fix IBM Integration Bus V9 PI28139 The APAR is available in fix pack 9.0.0.4 
https://www-304.ibm.com/support/docview.wss?rs=849&uid=swg24040542 [https://www-304.ibm.com/support/docview.wss?rs=849&uid=swg24040542] WebSphere Message Broker
V8 PI28139 The APAR is available in fix pack 8.0.0.6
http://www-01.ibm.com/support/docview.wss?rs=849&uid=swg24040259 [http://www-01.ibm.com/support/docview.wss?rs=849&uid=swg24040259] WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM Integration Bus could allow a local user to start and stop a service that they should not have access to |  |  |
| F2 | CVSS Base Score: 4 |  |  |
| F3 | (CVSS:3.0/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B072

```text
Help with Security Bulletin: Vulnerabilities in OpenSSL affect WebSphere MQ 5.3 for HP NonStop Server (CVE-2017-3735)
I need to understand details regarding Security Bulletin: Vulnerabilities in OpenSSL affect WebSphere MQ 5.3 for HP NonStop Server (CVE-2017-3735). What  versions of the product are affected?
```

答案正文：

```text
VULNERABILITY DETAILS
CVEID: CVE-2017-3735 [http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-3735]
DESCRIPTION: OpenSSL could allow a remote attacker to obtain sensitive information, caused by an error while parsing an IPAddressFamily extension in an X.509 certificate. An attacker could exploit this vulnerability to trigger an out-of-bounds read, resulting in an incorrect text display of the certificate.
CVSS Base Score: 4.3
CVSS Temporal Score: See https://exchange.xforce.ibmcloud.com/vulnerabilities/131047 [https://exchange.xforce.ibmcloud.com/vulnerabilities/131047] for the current score
CVSS Environmental Score*: Undefined
CVSS Vector: (CVSS:3.0/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N) 

AFFECTED PRODUCTS AND VERSIONS
All versions of WebSphere MQ 5.3 and MQ 8 for HPE NonStop Server

REMEDIATION/FIXES
For MQ 5.3 

 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * 
 * https://www-945.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm%7EWebSphere&product=ibm/WebSphere/WebSphere+MQ&release=5.3.1.14&platform=HP+NonStop&function=all
 * 

For MQ 8 
 * 

 * 
 * here
 * 

WORKAROUNDS AND MITIGATIONS
None [S1]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | All versions of WebSphere MQ 5.3 |  |  |
| F2 | MQ 8 for HPE NonStop Server |  |  |

评审人：________　日期：________　整题判断：________

## B073

```text
Is MQ or MQ Appliance impacted by Sweet32 Birthday Attack if we are running triple-DES cipher.?
```

答案正文：

```text
IBM MQ V9.0 

 * Apply Fix Pack 9.0.0.1 [http://www-01.ibm.com/support/docview.wss?uid=swg27048059]

IBM MQ V8.0 & IBM MQ Appliance V8.0  * Apply Fix Pack 8.0.0.6 [https://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/WebSphere+MQ&release=8.0.0.6&platform=All&function=all]. 
 * Apply Fix Pack 8.0.0.6 for IBM MQ Appliance [https://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~WebSphere&product=ibm/WebSphere/IBM+MQ+Appliance+M2000&release=8.0.0.6&platform=All&function=all].

IBM MQ V7.5.0  * Apply APAR IV90867 [http://www.ibm.com/support/fixcentral/swg/quickorder?parent=ibm%7EWebSphere&product=ibm/WebSphere/WebSphere+MQ&release=7.5.0.7&platform=All&function=aparId&apars=IV90867&source=fc]. [S1]
IBM MQ V7.1.0  * Apply APAR IV90867 [http://www.ibm.com/support/fixcentral/swg/quickorder?parent=ibm%7EWebSphere&product=ibm/WebSphere/WebSphere+MQ&release=7.1.0.8&platform=All&function=aparId&apars=IV90867&source=fc].

IBM MQ V7.0.1  * Users of MQ 7.0.1 should contact IBM support to request an interim fix for APAR IV90867.

WORKAROUNDS AND MITIGATIONS
All versions of MQ can mitigate the vulnerability either by switching to an alternative CipherSpec or by enabling secret key reset. 
Resetting SSL/TLS secret keys [http://www.ibm.com/support/knowledgecenter/SSFKSJ_9.0.0/com.ibm.mq.sec.doc/q014310_.htm] [S2]
```

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM MQ: Maintenance levels between 8.0.0.0 and 8.0.0.5, and 9.0.0.0 only |  |  |
| F2 | IBM MQ Appliance: Maintenance levels between 8.0.0.0 and 8.0.0.5 |  |  |
| F3 | IBM WebSphere MQ: Maintenance levels between 7.0.1.0 and 7.0.1.14 |  |  |
| F4 | IBM WebSphere MQ: Maintenance levels between 7.1.0.0 and 7.1.0.8 |  |  |
| F5 | IBM WebSphere MQ: Maintenance levels between 7.5.0.0 and 7.5.0.7 |  |  |

评审人：________　日期：________　整题判断：________

