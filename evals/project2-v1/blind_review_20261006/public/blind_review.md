# 盲评包

请勿打开另存的 key.json。只依据答案正文逐条评分：0=未覆盖或错误，1=部分覆盖，2=完整且正确。
正分需摘录正文中的原句；不得把来源附录、题目或模型信心当作答案。保持分歧，不强行合并。
请填写 blind_review.json 的 ratings、reviewer 和 review_date；没有事实条目的题填写 question_judgment（完整/部分/拒答/错误）及备注。
单事实例外单独报告，不进入主事实覆盖均值。技术产品版本号保留；评测系统身份信息未提供。

## B001

Help with Security Bulletin: MQSISTOP/STARTMSGFLOW commands with unauthorized user succeed affects WMB and IIB (CVE-2015-5011)
I need to understand details regarding Security Bulletin: MQSISTOP/STARTMSGFLOW commands with unauthorized user succeed affects IBM WebSphere Message Broker and IBM Integration Bus (CVE-2015-5011). Where can I find this information?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM Integration Bus could allow a local user to start and stop a service that they should not have access to |  |  |
| F2 | CVSS Base Score: 4 |  |  |
| F3 | (CVSS:3.0/AV:L/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B002

Why do I receive the message, "IKJ79154I INSTALLATION EXIT IKJEESX0 REQUESTED TERMINATION. " for a TSO SEND command?
If you issue the TSO SEND command in a batch job and receive this message:

IKJ79154I INSTALLATION EXIT IKJEESX0 REQUESTED TERMINATION.
IKJ79154I REASON CODE X'00000004'.

答案正文：

Code the appropriate security definitions for FEK.CMD.SEND and FEK.CMD.SEND.CLEAR. [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | coded a facility class for the FEK.CMD.SEND and FEK.CMD.SEND.CLEAR |  |  |

评审人：________　日期：________　整题判断：________

## B003

How do I change from shared to unshared connection?
in WAS, how do I change from shared to unshared connection. I am seeing connections max out and take a long time to release.

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B004

Invalid operation: result set is closed. ERRORCODE=-4470, SQLSTATE=null
When using BPM, I see runtime exceptions saying that this SQL error occurs: Invalid operation: result set is closed. ERRORCODE=-4470, SQLSTATE=null

For example:

CWLLG2015E: An unexpected runtime exception occurred. See exception for more details. Error: Wrapped com.lombardisoftware.core.TeamWorksRuntimeException:

答案正文：

*  A fix is available for IBM BPM V8.5.5.0 that ensures an explicit
    transaction would be used.  Transaction would only be closed
   after data is completely read from database. [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B005

Help with Security Bulletin: WMB and IIB Toolkit cannot connect to a remote WMB broker or IIB node with a TLS-compliant cipher (CVE-2015-0118)
I need to understand details regarding Security Bulletin: WebSphere Message Broker Toolkit and IBM Integration Toolkit cannot connect to a remote WebSphere Message Broker broker or IBM Integration Bus node with a TLS-compliant cipher (CVE-2015-0118). Where can I find this information?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B006

How can I export a private key from DataPower Gateway Appliance?
Is it possible to export a private key from DataPower Gateway Appliance?

答案正文：

Question: Can the HSM device store certificates? 

Answer: No. The HSM device only stores private keys.

Question: Can I export private keys from the HSM device?
Answer: Yes. Private keys can be exported from the HSM device using the crypto-export command and imported into another HSM device using the crypto-import command as long as the hardware platforms are compatible. 9235 appliances with HSM are compatible with each other in terms of exported HSM keys. 7198 and 7199 appliances with HSM are compatible with each other in terms of exported HSM keys. HSM keys cannot be exported from a 9235 appliance and imported into a 7198/7199 appliance or vice-versa. [S2]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | HSM-enabled DataPower appliances support the export of private keys using the crypto-export command |  |  |
| F2 | HSMs must be initialized and in the same key sharing domain on exporting and importing machines |  |  |
| F3 | The private key in question must be marked exportable at keygen time (see keygen's exportable option) |  |  |
| F4 | HSMs on exporting and importing machines must share internal key-wrapping keys (see hsm-clone-kwk command) |  |  |

评审人：________　日期：________　整题判断：________

## B007

Why is the test suite execution failing from Decision Center?
When executing a test suite from Decision Center the run may fail with an error message similar to:
 XU client error.
 GBRXU0448E: Plugin error.
 Unable to retrieve the engine manager.
 The parsing of the ruleset failed Problem occurred loading translation: Error when translating parameter "inputParameter": Cannot translate class "sample.InputParameter".

What can be causing this error?

答案正文：

First, ensure that the XOM and its dependencies were compiled for a Java version that is compatible with the JVM running the server that hosts Rule Execution Server. For example, classes that are compiled to comply with a Java 7 target would not work on a Java 6 JVM. [S1]
1. If working with ODM 8.5.0, please upgrade to ODM v8.5.1 (which contains the fix for APAR RS01418 [http://www.ibm.com/support/docview.wss?uid=swg1RS01418]) or later, to allow users mapped to resdeployers and resmonitors roles to be able to retrieve the HTDS Description file as well. If unable to do so immediately, make sure the user is mapped to the resAdministrators role, which is mapped to the Monitor role on WebSphere Application Server.

2. Ensure that the JDK level used for compiling the Java XOM classes is the same as the JDK level of the JVM used to run the application server. For example, the XOM could be compiled with Java 7 but the application server could be using Java 6. [S3]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B008

Help with Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808)
I need to understand details regarding Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808). Where can I find this information?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B009

Why is the reload() not clearing the attribute cache so I can see my newly updated LDAP data in real time?
You are leveraging the reload() functionality as described in the blog post:
  https://www.ibm.com/developerworks/community/blogs/PortalL2Thoughts/entry/how_to_programatically_refresh_data_from_ldap64?lang=en

to refresh the attribute cache after a change has been made to data within your LDAP. The purpose of this reload() is to update the data in real time on the Portal server. You discover that you are calling the reload(); however, the newly updated data is not immediately available to the application. How can this be fixed?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This APAR fixes the issue. It clears the cache properly even if base entry is different than name in repository. |  |  |
| F2 | The fix for this APAR is currently targeted for inclusion in fix packs 8.0.0.13 and 8.5.5.9. |  |  |

评审人：________　日期：________　整题判断：________

## B010

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

答案正文：

* In Application Manager, verify that the server information on the Taskmaster tab is correct. 
 * In Application Manager, verify that the Service tab points to the correct datacap.xml file and that the file correctly points from there to the application folder. 
 * When starting Rulerunner, verify that Application Manager and Datacap Studio are either not running or specifically in a state that does not lock any files. 
 * If not specified, Rulerunner will attempt to connect through both IPv4 and IPv6. The error will be generated in the log when the unused protocol is tried. For this situation, the error can be ignored. However, the protocol can be set through the Taskmaster tab in Application Manager to eliminate this cause of the error. 
 * Verify that the Rulerunner service is running under an account that has at least read permissions to the application folder. 
 * With multiple threads all attempting to establish connections, some attempts may fail because the server is momentarily busy processing another request. Verify that in the app file, tmservers section, all servers have retry="3". [S7]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B011

Does IBM DataPower Gateway Appliance support the HTTP CONNECT method?

答案正文：

知识库无法回答该问题。

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | an XML Firewall when configuring in the HTTP Options tab, where the user can configure the Proxy Host and Port |  |  |
| F2 | a Multi-Protocol Gateway when configuring an HTTP Proxy Policy in the User Agent |  |  |
| F3 | SSL Proxy requests will work using the CONNECT method for SSL Tunneling when using a Multi-Protocol Gateway when configuring in a User Agent's HTTP Proxy Policy |  |  |
| F4 | The XML Firewall service is not designed to use the CONNECT method for SSL Tunneling |  |  |

评审人：________　日期：________　整题判断：________

## B012

How to import a certificate in ITCAM for Data Power ?
How can I import a certificate in ITCAM for Data Power?

答案正文：

Import the certification file into the agent by doing the following command:

Note : You can use either .cer or .pem. 
Make sure the file is in ASCII not binary. 
Where the /usr/ITM/JRE is your Java location and <fileName> is your file name.

ex: 
/usr/ITM/JRE/aix526/jre/bin/keytool -import -trustcacerts -alias 
ligitalsso -keystore /usr/ITM/JRE/aix526/jre/bin/lib/security/cacerts 
-storepass <fileName> -file /NEWSSL-sscert.cer [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Import the certification file into the agent by doing the following command |  |  |
| F2 | You can use either .cer or .pem |  |  |
| F3 | Make sure the file is in ASCII not binary |  |  |

评审人：________　日期：________　整题判断：________

## B013

Can I disable RC4 cyphers in TIP?
How can one disable the RC4 cypers in Tivoli Integrated Portal?

答案正文：

To remove RC4 ciphers:


 1. Log into the Websphere Application server and navigate to:
    SSL certificate and key management > SSL configurations > NodeDefaultSSLSettings > Quality of protection (QoP)
    
    
 2. Select the *RC4* ciphers from the "Selected ciphers" list, and then click the "<<Remove" button.
    
    
 3.  Click the "Apply" button, and then the "Save (to the master configuration)" link.
    
    
 4. Restart TIP. [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Log into the Websphere Application server and navigate to: SSL certificate and key management > SSL configurations > NodeDefaultSSLSettings > Quality of protection (QoP) |  |  |
| F2 | Select the *RC4* ciphers from the "Selected ciphers" list, and then click the "<<Remove" button |  |  |
| F3 | Click the "Apply" button, and then the "Save (to the master configuration)" link |  |  |
| F4 | Restart TIP |  |  |

评审人：________　日期：________　整题判断：________

## B014

Security Bulletin: IBM MQ and IBM MQ Appliance Shared memory leak caused by MQ applications using dynamic queues (CVE-2017-1283)
I need to understand details regarding Security Bulletin: IBM MQ and IBM MQ Appliance Shared memory leak caused by MQ applications using dynamic queues (CVE-2017-1283). Where can I find this information?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM WebSphere MQ could allow an authenticated user to cause a shared memory leak by MQ applications using dynamic queues, which can lead to lack of resources for other MQ applications |  |  |
| F2 | CVSS Base Score: 3.1 |  |  |
| F3 | (CVSS:3.0/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:N/A:L) |  |  |

评审人：________　日期：________　整题判断：________

## B015

Error running krzgrant.sql script provided with 6.3.1.2-TIV-ITM_KRZ-IF0003.tar
When running the krzgrant.sql script provided in the package - 6.3.1.2-TIV-ITM_KRZ-IF0003.tar get the following errors:

ERROR at line 1:
ORA-00942: table or view does not exist ORA-06512: at line 50 

How to correct this?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Run the krzgrant.sql script |  |  |
| F2 | 6.3.1-TIV-ITM_KRZ-FP0001 |  |  |

评审人：________　日期：________　整题判断：________

## B016

How to start PC DMgr as a Windows service?
hi all. I just installed BPM 8.5.0.1 Process Center on a Windows 2008 R2 cloud server. The default BPM85 typical installation installs ProcessCenter Quickstart web page for starting the Dmgr and NodeMgr servers using the installation admin user . However, logout stops the services started by and attached to the admin user. I need to have this ProcessCenter (and Deployment Env Process SErvers) BPM85 DMgr / Node/ WASND started as a managed Windows managed service. I didn't see a Service Definition page to select run as Windows service. Can I possibly run BPMConfig -start dmgrprofile as a Windows service or is a profile update to my dmgr (hope not) needed to do this?

答案正文：

IBM Specifying the profile path in the BPMConfig properties file for IBM Business Process Manager (BPM) - United States

BPMConfig; profile; path; directory TECHNOTE (FAQ)

QUESTION
 How do you specify the profile path in the configuration properties file for IBM Business Process Manager so you can use it with the BPMConfig command? 

ANSWER [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Place the WASServiceCmd.exe utility in the following directory: install_root\bin |  |  |
| F2 | Launch the command from the command line |  |  |
| F3 | The WASServiceCmd utility prompts you to select specific options and settings from a list and then calls the WASService.exe command passing all selected parameters |  |  |

评审人：________　日期：________　整题判断：________

## B017

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

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | It is an known limitation of current DB2 V9.7 and above versions' runstats |  |  |

评审人：________　日期：________　整题判断：________

## B018

Why is the reload() not clearing the attribute cache so I can see my newly updated LDAP data in real time?
You are leveraging the reload() functionality as described in the blog post:
  https://www.ibm.com/developerworks/community/blogs/PortalL2Thoughts/entry/how_to_programatically_refresh_data_from_ldap64?lang=en

to refresh the attribute cache after a change has been made to data within your LDAP. The purpose of this reload() is to update the data in real time on the Portal server. You discover that you are calling the reload(); however, the newly updated data is not immediately available to the application. How can this be fixed?

答案正文：

知识库无法回答该问题。

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This APAR fixes the issue. It clears the cache properly even if base entry is different than name in repository. |  |  |
| F2 | The fix for this APAR is currently targeted for inclusion in fix packs 8.0.0.13 and 8.5.5.9. |  |  |

评审人：________　日期：________　整题判断：________

## B019

CQWEB  can\'t retrieve repository dropdown list options in RedHat Linux, how to deal with it ?
I setup a cq demo env in redhat linux with oracle database, CQ 7.1.2, LRKS 8.1.3,  Linux CQ client can login CQ as the following picture 1, but CQWEB login page can't retrieve the repository dropdown list options as the following picture 2.  I used cqreg to register CQ database:

cqreg add_dbset -v ORACLE -s 192.168.0.84 -d ESBDB -u cqadmin -p cqadmin -dbset CQ_DEMO_ORACLE -co LOB_TYPE=CLOB -force

What's matter for this happen?

答案正文：

About the default database path: 
When ClearQuest tries to connect to a database, it will first look if the CQ_DATABASES variable has been set, and if set, it will use this variable to determine where the database is registered. With the setenv command, you can set a user or system variable. (This is under the cshell. If using bash, use the env command and then export the env variable with the export command.) If the default database path has not been set, you can set it by entering the variable CQ_DATABASES. This should point to:  * 
 * 
   /opt/rational/clearquest/CQDB_rgys/cqdb_registry/ [S1]
Run cqreg initialize. The add_dbset command will run successfully afterwards. However, should the same error persist, make sure the command is run as the root user. 



Also make sure that the CQ_DATABASES environment variable is set to the desired registry path. If it is not, set the variable accordingly, then run the previously mentioned commands again. [S6]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Normally, at the end of a ClearQuest installation on UNIX® based platforms, the cqreg initialize command runs automatically |  |  |
| F2 | The command creates the registry structure for database sets |  |  |
| F3 | During the installation, the command did not run successfully |  |  |

评审人：________　日期：________　整题判断：________

## B020

Why are some Datatypes corrupt after Impact cluster failover/failback ?
Running Impact 7.1.0.11. The symptom is whenever Impact does a failover, a couple DataTypes
turn out empty.

I've checked the type files before and after Impact failover and the difference happens in the property

*.SQL.USERPARAMETERS

This property no longer exists for the corrupted datatypes".

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Add the property to $NCHOME/impact/etc/<SERVERNAME>_server.props file where size limit can be 8192, 16384, 32768, etc.. |  |  |
| F2 | The property would have to be added to all ImpactServers in the Cluster and would require a restart to enable |  |  |
| F3 | ensure that there are no trailing white-space characters on the property |  |  |
| F4 | The APAR is not an issue in Impact 6 and 7, but one would still have to include this property with an appropriate value |  |  |
| F5 | The character length includes the whole USERPARAMETERS property name as well as the definition |  |  |

评审人：________　日期：________　整题判断：________

## B021

Help with Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808)
I need to understand details regarding Security Bulletin: Security vulnerabilities have been identified in IBM DB2 shipped with WebSphere Remote Server (CVE-2015-2808). Where can I find this information?

答案正文：

VULNERABILITY DETAILS
For vulnerability details, see the security bulletin Vulnerability in RC4 stream cipher affects IBM DB2 LUW (CVE-2015-2808). [http://www.ibm.com/support/docview.wss?uid=swg21717865]

AFFECTED PRODUCTS AND VERSIONS
 

Principal Product and Version(s) Affected Supporting Product and Version WebSphere Remote Server version V6.2, 6.2.1, 7.0, 7.1, 7.1.1, 7.1.2, 8.5 IBM DB2 Workgroup Server Edition 
V9.5, 9.7, 10.1, 10.5 [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B022

Unable to view batches in DotEdit
Hi all,

Is there any limitation to view batches in Dot Edit client application, because I am unable to see batches with QID more than 1119.

Also unable to see batches with status as "Pending".

答案正文：

Please do the following: 

 1. Backup the \Datacap\DotEdit\apps.ini file. If the file does not exist, create a new one or copy it from \Datacap\tmweb.net. 
 2. Open it in notepad.exe or other editor. 
 3. Find the app to be modified (for example [APT]). If it does not exist, create a new section with the application name listed between square brackets. 
 4. Add a new line containing BatchLimit=xxx, where xxx is the number of batches to be displayed. 
 5. Save the file. [S2]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Backup the \Datacap\DotEdit\apps.ini file |  |  |
| F2 | If the file does not exist, create a new one or copy it from \Datacap\tmweb.net |  |  |
| F3 | Find the app to be modified (for example [APT]). If it does not exist, create a new section with the application name listed between square brackets |  |  |
| F4 | Add a new line containing BatchLimit=xxx, where xxx is the number of batches to be displayed |  |  |
| F5 | Save the file |  |  |

评审人：________　日期：________　整题判断：________

## B023

Improve Performance of Decision Center and Rule Team Server (RTS)
How can I improve the performance of ODM Decision Center and WebSphere ILOG Rule Team Server (RTS)?

答案正文：

If the above recommendations do not help, contact IBM support with the following information:  * Environment details including the application server, JDK, database and operating system. 
 * RTS server logs, including FFDC logs if working with WebSphere Application Server. 
 * The typical behavior of RTS users: Are they mostly viewing or editing? Is there a lot of ruleset generation going on simultaneously while editing? 
 * The typical load on RTS, including the number of simultaneous users and number of rulesets being generated [S1]
* Reduce the memory footprint of the ruleset by setting the ruleset property ruleset.bom.enabled [http://publib.boulder.ibm.com/infocenter/dmanager/v7r5/index.jsp?topic=%2Fcom.ibm.dserver.res%2FContent%2FBusiness_Rules%2F_pubskel%2FInfocenter_Primary%2Fps_DS_RES_Console_OH1654.html] to "false [http://publib.boulder.ibm.com/infocenter/dmanager/v7r5/index.jsp?topic=%2Fcom.ibm.dserver.res%2FContent%2FBusiness_Rules%2F_pubskel%2FInfocenter_Primary%2Fps_DS_Rule_Execution_Server1564.html]" to remove support for BOM based serialization. This property is set to "true" by default when extracting rulesets from Rule Team Server (RTS) and Decision Center, and needs to be explicitly set to "false" in order to deactivate it. (You should set it to "true" if you need to generate an Excel report from a Test Suite/Simulation in RTS or Decision Center.) [S2]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B024

Why the Editor for Messages logon page does not work?
We have Editor for Messages installed on a Windows server. Users are accessing the web UI from a terminal server session that has been replaced recently. Users cannot login anymore from the new environment.

The fails as follows : the Editor for Messages logon page loads but when the user wants to validate their user/password by clicking on the "login" button, nothing occurs.

答案正文：

知识库无法回答该问题。

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Editor for Messages supports Microsoft Internet Explorer only |  |  |
| F2 | Mozilla Firefox and Google Chrome are not supported |  |  |
| F3 | IE 6, IE 7, IE 8, IE 9 (compatibility view), IE 10(Compatibility view), IE 11(Compatibility view) |  |  |

评审人：________　日期：________　整题判断：________

## B025

How to resolve DataPower firmware loading error % Loading firmware failed: Internal receive API error (3)?
Message % Loading firmware failed: Internal receive API error (3) was observed during firmware update. How do you resolve this issue?

答案正文：

ERROR DESCRIPTION
 *  When applying an IBM MQ Appliance firmware update, the following
   message will be seen:
   
   Invoking dynamic loader
   % Loading firmware failed: Internal receive API error (3)
   
   The installation may succeed despite this error. [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B026

Help with Security Bulletin: Multiple vulnerabilities in IBM® Java SDK affect WebSphere Enterprise Service Bus (CVE-2015-2613)
I would like to know details on how vulnerabilities in IBM Java SDK affect Websphere Application Server and in turn, Websphere Enterprise Service Bus product.

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | An unspecified vulnerability and Java SE Embedded related to the JCE component could allow a remote attacker to obtain sensitive information |  |  |
| F2 | CVSS Base Score: 5 |  |  |
| F3 | (AV:N/AC:L/Au:N/C:P/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B027

MQSeries Events correlation
How are MQSeries Events cleared?

答案正文：

ANSWER
The MQSeries Events workspace displays data from the Current Events attribute group. Since this data is stored in memory, stopping and restarting the MQ Monitoring agent will clear all the data in the Current Events table. [S2]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The MQSeries Events workspace displays data from the Current Events attribute group |  |  |
| F2 | Since this data is stored in memory, stopping and restarting the MQ Monitoring agent will clear all the data in the Current Events table |  |  |

评审人：________　日期：________　整题判断：________

## B028

Is WAS TE v7.0.0.41 available for RAD?
Is WebSphere Application Server 7.0 Test Environment Extension (WTE) v 7.0.0.41 available for Rational Application Developer for WebSphere Software (RAD) ?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This download includes the following update to the WebSphere Application Server v7.0 Test Environment extension included with Rational Software Delivery Platform products |  |  |
| F2 | IBM WebSphere Application Server Version 7 Fix Pack 41 also known as version 7.0.0.41 |  |  |

评审人：________　日期：________　整题判断：________

## B029

Help with Security Bulletin: Vulnerabilities in OpenSSL affect WebSphere MQ 5.3 for HP NonStop Server (CVE-2017-3735)
I need to understand details regarding Security Bulletin: Vulnerabilities in OpenSSL affect WebSphere MQ 5.3 for HP NonStop Server (CVE-2017-3735). What  versions of the product are affected?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | All versions of WebSphere MQ 5.3 |  |  |
| F2 | MQ 8 for HPE NonStop Server |  |  |

评审人：________　日期：________　整题判断：________

## B030

Recurrent RES StaleConnectionException
How to prevent rule execution failing because of recurrent StaleConnectionException on ODM 8.8 Rule Execution Server?

答案正文：

Configure the WebSphere Application Server data source connection pool [http://publib.boulder.ibm.com/infocenter/wasinfo/v7r0/index.jsp?topic=/com.ibm.websphere.nd.multiplatform.doc/info/ae/ae/udat_conpoolset.html] so as to eliminate occurrences of StaleConnectionException : 

 * Set the Minimum connections to 0 to avoid situations where a connection is kept in the pool to meet the minimum requirement, even though it may have been idle for longer than Unused timeout 
 * Set the values for Unused timeout and Reap timeout so that the sum does not exceed any network level idle connection timeout [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Configure the WebSphere Application Server data source connection pool so as to eliminate occurrences of StaleConnectionException |  |  |
| F2 | Set the Minimum connections to 0 to avoid situations where a connection is kept in the pool to meet the minimum requirement, even though it may have been idle for longer than Unused timeout |  |  |
| F3 | Set the values for Unused timeout and Reap timeout so that the sum does not exceed any network level idle connection timeout |  |  |

评审人：________　日期：________　整题判断：________

## B031

Help with Security Bulletin: Vulnerability in Diffie-Hellman ciphers affects IBM Image Construction and CompositionTool. (CVE-2015-4000)
I need to understand details regarding "Security Bulletin: Vulnerability in Diffie-Hellman ciphers affects IBM Image Construction and CompositionTool. (CVE-2015-4000". Where can I find this information?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The TLS protocol could allow a remote attacker to obtain sensitive information, caused by the failure to properly convey a DHE_EXPORT ciphersuite choice |  |  |
| F2 | An attacker could exploit this vulnerability using man-in-the-middle techniques to force a downgrade to 512-bit export-grade cipher |  |  |
| F3 | commonly referred to as "Logjam" |  |  |
| F4 | CVSS Base Score: 4.3 |  |  |
| F5 | (AV:N/AC:M/Au:N/C:P/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B032

When should I use conversation sharing in DataPower MQ queue managers?
MQ version 7.0 introduced a new feature, conversation sharing. Are there any special values on DataPower when configuring conversation sharing?

答案正文：

IBM WebSphere MQ server version 7.0 and later releases provide sharing conversations (SHARECNV) attribute on SVRCONN channel that specifies the maximum number of conversations that can share each TCP/IP channel instance. This feature can be configured in DataPower as it uses client connection with queue manager SVRCONN channel. 
The default setting of sharing conversations (SHARECNV) value is zero in DataPower mq-qm object. The same default value for MQ SVRCONN channel is 10. The sharing conversations value is 
negotiated between MQ server and DataPower and the lower value takes effect. However, in current versions of the DataPower firmware, the sharing conversations setting of 1 is treated as 0 when negotiating with MQ server.

There are three use cases to configure Sharing Conversations in DataPower mq-qm object: 

Case #1 : The negotiated sharing conversations value is 0 - The channel runs in a mode similar to WebSphere MQ V6 and does not uses features such as [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The default setting of sharing conversations (SHARECNV) value is zero in DataPower mq-qm object |  |  |
| F2 | The same default value for MQ SVRCONN channel is 10 |  |  |
| F3 | The sharing conversations value is negotiated between MQ server and DataPower and the lower value takes effect |  |  |
| F4 | in current versions of the DataPower firmware, the sharing conversations setting of 1 is treated as 0 when negotiating with MQ server |  |  |

评审人：________　日期：________　整题判断：________

## B033

My SystemOut.log is overfilled by messages SECJ0371W (LTPA token expired). I am sick and tired of them. Can I disable them?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | A security custom property will be used to disable the logging of the SECJ0371W message |  |  |
| F2 | com.ibm.websphere.security.ltpa.disableSECJ0371W=true |  |  |

评审人：________　日期：________　整题判断：________

## B034

Why Plug-in log file reports an error message after install & configure the WebSphere Plugin 8.5 version on a Apache 2.4 webserver.
During web server start-up, errors like the following will be logged into the Plug-in log file (http_plugin.log):

ERROR: lib_security: loadSecurityLibrary: Failed to load gsk library from /opt/IBM/WebSphere/Plugins/gsk8/gsk8_64 ERROR: ws_transport: transportInitializeSecurity: Unable to load security library ERROR: ws_server: serverAddTransport: Failed to initialize security ERROR: ws_server: serverAddTransport: HTTPS Transport is skipped

Note: This is after install & configure the WebSphere Plugin 8.5 version on a Apache 2.4 webserver  on a Linux platform

答案正文：

To resolve the problem, you must set the LD_LIBRARY_PATH environment variable to point to the library directory of the GSKit that comes with the IBM web server Plug-in. The precise directory location will depend of the version of Plug-in, and on the bit depth being used (32-bit or 64-bit). [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | you must set the LD_LIBRARY_PATH environment variable |  |  |
| F2 | to point to the library directory of the GSKit that comes with the IBM web server Plug-in |  |  |
| F3 | The precise directory location will depend of the version of Plug-in, and on the bit depth being used (32-bit or 64-bit) |  |  |

评审人：________　日期：________　整题判断：________

## B035

Help with Security Bulletin: TLS padding vulnerability affects IBM PureApplication System (CVE-2014-8730)
I need to understand details regarding "Security Bulletin: TLS padding vulnerability affects IBM PureApplication System (CVE-2014-8730)". Where can I find this information?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | IBM PureApplication Server bundles IBM HTTP Server, which could allow a remote attacker to obtain sensitive information, caused by the failure to check the contents of the padding bytes when using CBC cipher suites of some TLS implementations |  |  |
| F2 | A remote user with the ability to conduct a man-in-the-middle attack could exploit this vulnerability via a POODLE (Padding Oracle On Downgraded Legacy Encryption) like attack |  |  |
| F3 | CVSS Base Score: 4.3 |  |  |
| F4 | (AV:N/AC:M/Au:N/C:P/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B036

Security Bulletin: MQ Explorer directory created with owner '555' on Linux x86-64 vulnerability affects IBM MQ (CVE-2016-6089)
I need to understand details regarding Security Bulletin: MQ Explorer directory created with owner '555' on Linux x86-64 vulnerability affects IBM MQ (CVE-2016-6089). Where can I find this information?

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B037

Help with Security Bulletin: The WebAdmin context for WMB V8 allows directory listings (CVE-2016-6080)
I need to understand details regarding Security Bulletin: The WebAdmin context for WebSphere Message Broker Version 8 allows directory listings (CVE-2016-6080). Where can I find this information?
  0

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | The WebAdmin context for WebSphere Message Broker allows directory listings, which could disclose sensitive information to the attacker |  |  |
| F2 | CVSS Base Score: 5.3 |  |  |
| F3 | (CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N) |  |  |

评审人：________　日期：________　整题判断：________

## B038

Unable to open profile from P8 Content Engine Configuration manager (CMUI) on Redhat Linux 7.2, getting GPF and javacore dump.
Launch configmgr then try to open an existing profile. Once I click ok on the dialog box to
"Verify your application server setting before proceeding..." Configuration manager would crash and GPF. I can see the javacore.txt and dmp file created.
The javacore.txt contains the following:

0SECTION TITLE subcomponent dump routine NULL =============================== 1TICHARSET UTF-8 1TISIGINFO Dump Event "gpf" (00002000) received 1TIDATETIME Date: 2016/05/05 at 04:53:30 1TIFILENAME Javacore filename: /opt/IBM/FileNet/ContentEngine/tools/configure/javacore.20160505.045330.25035.0002.txt 1TIREQFLAGS Request Flags: 0x81 (exclusive+preempt) 1TIPREPSTATE Prep State: 0x100 (trace_disabled) 1TIPREPINFO Exclusive VM access not taken: data may not be consistent across javacore sections NULL ------------------------------------------------------------------------ 0SECTION GPINFO subcomponent dump routine NULL ================================ 2XHOSLEVEL OS Level : Linux 3.10.0-327.13.1.el7.x86_64 2XHCPUS Processors - 3XHCPUARCH Architecture : x86 3XHNUMCPUS How Many : 1 3XHNUMASUP NUMA is either not supported or has been disabled by user NULL
1XHEXCPCODE J9Generic_Signal_Number: 00000004 1XHEXCPCODE Signal_Number: 0000000B 1XHEXCPCODE Error_Value: 00000000 1XHEXCPCODE Signal_Code: 00000080 1XHEXCPCODE Handler1: F72A2E6A 1XHEXCPCODE Handler2: F724D00A 1XHEXCPCODE InaccessibleAddress: 00000000 NULL
1XHEXCPMODULE Module: /lib/libcairo.so.2 1XHEXCPMODULE Module_base_address: D55FC000

This is a Redhat Linux 7.2 environment with Content Platform Engine CPE 5.2.1.4.

答案正文：

RESOLVING THE PROBLEM
Install the missing libraries "adwaita-gtk2-theme" (32 and 64 bit) and "adwaita-gtk3-theme" 64 bit. Please contact RedHat to obtain the missing libraries. [S4]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | "adwaita-gtk2-theme" (32 and 64 bit) |  |  |
| F2 | "adwaita-gtk3-theme" 64 bit |  |  |
| F3 | Please contact RedHat to obtain the missing libraries |  |  |

评审人：________　日期：________　整题判断：________

## B039

Why are some Datatypes corrupt after Impact cluster failover/failback ?
Running Impact 7.1.0.11. The symptom is whenever Impact does a failover, a couple DataTypes
turn out empty.

I've checked the type files before and after Impact failover and the difference happens in the property

*.SQL.USERPARAMETERS

This property no longer exists for the corrupted datatypes".

答案正文：

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

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Add the property to $NCHOME/impact/etc/<SERVERNAME>_server.props file where size limit can be 8192, 16384, 32768, etc.. |  |  |
| F2 | The property would have to be added to all ImpactServers in the Cluster and would require a restart to enable |  |  |
| F3 | ensure that there are no trailing white-space characters on the property |  |  |
| F4 | The APAR is not an issue in Impact 6 and 7, but one would still have to include this property with an appropriate value |  |  |
| F5 | The character length includes the whole USERPARAMETERS property name as well as the definition |  |  |

评审人：________　日期：________　整题判断：________

## B040

Error TASK001X while upgrading Portal 8.0.0.1 to 8.0.0.1 CF14 during import-nodes sub-task

答案正文：

Please make the following change in the WAS Admin Console...
Applications > WebSphere enterprise applications >
JavaContentRepository > Target specific application status > Check the
box for the WebSphere_Portal server > Click Enable Auto Start > Save
changes > restart Portal [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | Applications > WebSphere enterprise applications > JavaContentRepository |  |  |
| F2 | Target specific application status > Check the box for the WebSphere_Portal server > Click Enable Auto Start |  |  |
| F3 | Save changes > restart Portal |  |  |
| F4 | After making this change please attempt the CF upgrade again |  |  |

评审人：________　日期：________　整题判断：________

## B041

How to use the LIKE operator, wildcard and special characters in your IBM FileNet Content Platform Engine Sweep's Filter Expression?

答案正文：

IBM How to use the LIKE operator, wildcard and special characters in your IBM FileNet Content Platform Engine Sweep's Filter Expression - United States

TECHNOTE (FAQ)

QUESTION
 How to use the LIKE operator, wildcard and special characters in your IBM FileNet Content Platform Engine Sweep's Filter Expression? 

CAUSE
A sweep is an instance of a background service that you configure to process objects in a database table or some other set of items. To optimize sweep performance, you can optionally make the filter expression for the sweep a part of the WHERE clause of the sweep query. This inclusion means that the sweep retrieves only those database rows that satisfy the filter conditions.
The criteria is expressed in terms of properties and values of the objects that are targeted by the sweep. The syntax is a subset of the SQL syntax for the WHERE clause. [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |

评审人：________　日期：________　整题判断：________

## B042

Why does my upgrade to Portal 8001 CF14 fail with the following errors, ADMA5008E, ADMA0063E, ADMA5069E, WASX7017E?

答案正文：

- Shut-down the DMGR
- Clear out the contents of the following directories:

dmgr_profile/wstemp
dmgr_profile/temp

- Restart the DMGR.
- Re-attempt the upgrade




This can also occur when the DMGR is running as a non-root user. If so, please stop and re-start the DMGR as root and attempt the upgrade again. [S1]

| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |
| --- | --- | --- | --- |
| F1 | This exception can happen during ejbdeploy after the WebSphere Application Server has been upgraded, and old OSGI cache remains for the ejbdeploy tool |  |  |
| F2 | The OSGI class of the ejbdeploy tool contains class information within the deploytool folder and can become stale if the content inside deploytool has changed |  |  |

评审人：________　日期：________　整题判断：________

