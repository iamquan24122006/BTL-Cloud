"""Generate a credential-free JMeter 5.6 read workload for the private lab."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def prop(parent, name, value, kind="stringProp"):
    ET.SubElement(parent, kind, name=name).text = str(value).lower() if isinstance(value, bool) else str(value)


def element(tree, kind, name, gui, **attributes):
    item = ET.SubElement(tree, kind, guiclass=gui, testclass=kind, testname=name, enabled="true", **attributes)
    children = ET.SubElement(tree, "hashTree")
    return item, children


def http(tree, name, path, method="GET", arguments=None):
    sampler, children = element(tree, "HTTPSamplerProxy", name, "HttpTestSampleGui")
    args = ET.SubElement(sampler, "elementProp", name="HTTPsampler.Arguments", elementType="Arguments")
    collection = ET.SubElement(args, "collectionProp", name="Arguments.arguments")
    for key, value in (arguments or {}).items():
        argument = ET.SubElement(collection, "elementProp", name=key, elementType="HTTPArgument")
        prop(argument, "HTTPArgument.always_encode", True, "boolProp")
        prop(argument, "Argument.name", key)
        prop(argument, "Argument.value", value)
        prop(argument, "Argument.metadata", "=")
    for key, value in {"HTTPSampler.path": path, "HTTPSampler.method": method,
                       "HTTPSampler.contentEncoding": "UTF-8", "HTTPSampler.connect_timeout": 10000,
                       "HTTPSampler.response_timeout": 45000}.items():
        prop(sampler, key, value)
    for key, value in {"HTTPSampler.follow_redirects": True, "HTTPSampler.auto_redirects": False,
                       "HTTPSampler.use_keepalive": True}.items():
        prop(sampler, key, value, "boolProp")
    return children


def assertion(tree, script):
    item, _ = element(tree, "JSR223Assertion", "Business assertion", "TestBeanGUI")
    prop(item, "scriptLanguage", "groovy")
    prop(item, "cacheKey", "true")
    prop(item, "script", script)


def main():
    root = ET.Element("jmeterTestPlan", version="1.2", properties="5.0", jmeter="5.6.3")
    tree = ET.SubElement(root, "hashTree")
    plan, tree = element(tree, "TestPlan", "Moodle authenticated reads", "TestPlanGui")
    prop(plan, "TestPlan.comments", "Synthetic accounts only. 50% course / 50% file reads; no submission writes or browser rendering. Credentials come from a private CSV.")
    prop(plan, "TestPlan.functional_mode", False, "boolProp")
    prop(plan, "TestPlan.serialize_threadgroups", False, "boolProp")
    arguments = ET.SubElement(plan, "elementProp", name="TestPlan.user_defined_variables", elementType="Arguments")
    ET.SubElement(arguments, "collectionProp", name="Arguments.arguments")
    group, children = element(tree, "ThreadGroup", "Independent user sessions", "ThreadGroupGui")
    prop(group, "ThreadGroup.on_sample_error", "stopthread")
    loop = ET.SubElement(group, "elementProp", name="ThreadGroup.main_controller", elementType="LoopController")
    prop(loop, "LoopController.continue_forever", False, "boolProp")
    prop(loop, "LoopController.loops", 1)
    prop(group, "ThreadGroup.num_threads", "${__P(users,2)}")
    prop(group, "ThreadGroup.ramp_time", "${__P(ramp,10)}")
    prop(group, "ThreadGroup.scheduler", True, "boolProp")
    prop(group, "ThreadGroup.duration", "${__P(duration,120)}")
    prop(group, "ThreadGroup.delay", 0)
    csv, _ = element(children, "CSVDataSet", "Private unique accounts", "TestBeanGUI")
    for key, value in {"filename": "${__P(users_csv)}", "fileEncoding": "UTF-8", "variableNames": "username,password",
                       "delimiter": ",", "shareMode": "shareMode.all"}.items():
        prop(csv, key, value)
    for key, value in {"ignoreFirstLine": True, "quotedData": True, "recycle": False, "stopThread": True}.items():
        prop(csv, key, value, "boolProp")
    defaults, _ = element(children, "ConfigTestElement", "Selected site origin", "HttpDefaultsGui")
    for key, value in {"HTTPSampler.domain": "${__P(host,localhost)}", "HTTPSampler.port": "${__P(port,8080)}",
                       "HTTPSampler.protocol": "${__P(protocol,http)}", "HTTPSampler.implementation": "HttpClient4"}.items():
        prop(defaults, key, value)
    cookie, _ = element(children, "CookieManager", "Separate cookie jar per user", "CookiePanel")
    ET.SubElement(cookie, "collectionProp", name="CookieManager.cookies")
    prop(cookie, "CookieManager.clearEachIteration", False, "boolProp")
    prop(cookie, "CookieManager.policy", "standard")
    login = http(children, "Login form", "/login/index.php")
    extractor, _ = element(login, "RegexExtractor", "Login CSRF token", "RegexExtractorGui")
    for key, value in {"RegexExtractor.useHeaders": "false", "RegexExtractor.refname": "logintoken",
                       "RegexExtractor.regex": 'name="logintoken"[^>]*value="([^"]+)"',
                       "RegexExtractor.template": "$1$", "RegexExtractor.default": "TOKEN_MISSING",
                       "RegexExtractor.match_number": "1"}.items():
        prop(extractor, key, value)
    assertion(login, "if (vars.get('logintoken') == 'TOKEN_MISSING') { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('Login token missing'); }")
    login = http(children, "Login", "/login/index.php", "POST",
                 {"username": "${username}", "password": "${password}", "logintoken": "${logintoken}"})
    assertion(login, "if (prev.getURL().getPath().contains('/login/')) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('Authentication failed'); }")
    loop, loopchildren = element(children, "LoopController", "Read workload until duration ends", "LoopControlPanel")
    prop(loop, "LoopController.continue_forever", False, "boolProp")
    prop(loop, "LoopController.loops", -1)
    timer, _ = element(loopchildren, "UniformRandomTimer", "Think 3 to 8 seconds", "UniformRandomTimerGui")
    prop(timer, "ConstantTimer.delay", "${__P(think_ms,3000)}")
    prop(timer, "RandomTimer.range", "${__P(think_range_ms,5000)}")
    page = http(loopchildren, "Course", "/course/view.php?id=${__P(course_id,2)}")
    assertion(page, "if (prev.getURL().getPath() != '/course/view.php' || !prev.getResponseDataAsString().contains(props.getProperty('course_marker', 'Cloud Integration Lab'))) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('Private course assertion failed'); }")
    file = http(loopchildren, "Download", "${__P(file_path)}")
    assertion(file, "def hash = java.security.MessageDigest.getInstance('SHA-256').digest(prev.getResponseData()).encodeHex().toString(); if (hash != props.getProperty('file_sha256')) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('File integrity or authorization assertion failed'); }")
    destination = ROOT / "tests/load/moodle-read.jmx"
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
    print(destination)


if __name__ == "__main__":
    main()
