"""Generate the P0 60/20/10/10 logical-action workload from the read smoke plan."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.make_jmeter_plan import assertion, element, http, main as make_read_plan, prop


def main():
    make_read_plan()
    source = Path(__file__).resolve().parents[1] / "tests/load/moodle-read.jmx"
    tree = ET.parse(source)
    root = tree.getroot()
    group = root.find(".//ThreadGroup/../hashTree")
    if group is None:
        raise ValueError("Read plan thread group is missing")
    # Capture the original login samplers and their token/assertion children.
    entries = list(group)
    login_pairs = []
    for index, entry in enumerate(entries):
        if entry.tag == "HTTPSamplerProxy" and entry.get("testname") in ("Login form", "Login"):
            login_pairs += [deepcopy(entry), deepcopy(entries[index + 1])]
    login_post_tree = next(entries[i + 1] for i, e in enumerate(entries)
                           if e.tag == "HTTPSamplerProxy" and e.get("testname") == "Login")
    token, _ = element(login_post_tree, "RegexExtractor", "Logout session key", "RegexExtractorGui")
    for key, value in {"RegexExtractor.useHeaders": "false", "RegexExtractor.refname": "sesskey",
                       "RegexExtractor.regex": '"sesskey":"([^"]+)"', "RegexExtractor.template": "$1$",
                       "RegexExtractor.default": "SESSION_KEY_MISSING", "RegexExtractor.match_number": "1"}.items():
        prop(token, key, value)
    # Reauthentication also refreshes the session key after each login.
    login_pairs[-1] = deepcopy(login_post_tree)
    loop = next(e for e in group if e.tag == "LoopController")
    children = list(group)[list(group).index(loop) + 1]
    for item in list(children):
        if item.tag != "UniformRandomTimer" and not (item.tag == "hashTree" and len(item) == 0):
            children.remove(item)
    _, choices = element(children, "SwitchController", "Choose one logical action", "SwitchControllerGui")
    selector = list(children)[-2]
    prop(selector, "SwitchController.value", "${__Random(0,9,)}")
    for number in range(10):
        _, branch = element(choices, "GenericController", str(number), "LogicControllerGui")
        if number < 6:
            page = http(branch, "Course", "/course/view.php?id=${__P(course_id,2)}")
            assertion(page, "if (prev.getURL().getPath() != '/course/view.php' || !prev.getResponseDataAsString().contains(props.getProperty('course_marker'))) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('Private course assertion failed'); }")
        elif number < 8:
            page = http(branch, "Download", "${__P(file_path)}")
            assertion(page, "def hash = java.security.MessageDigest.getInstance('SHA-256').digest(prev.getResponseData()).encodeHex().toString(); if (hash != props.getProperty('file_sha256')) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('File assertion failed'); }")
        elif number == 8:
            page = http(branch, "Assignment view", "/mod/assign/view.php?id=${__P(assignment_id)}")
            assertion(page, "if (prev.getURL().getPath() != '/mod/assign/view.php' || !prev.getResponseDataAsString().contains(props.getProperty('assignment_marker'))) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('Assignment assertion failed'); }")
        else:
            page = http(branch, "Logout", "/login/logout.php?sesskey=${sesskey}&loginpage=1")
            assertion(page, "if (vars.get('sesskey') == 'SESSION_KEY_MISSING' || !prev.getURL().getPath().contains('/login/')) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage('Logout failed'); }")
            for item in login_pairs:
                branch.append(deepcopy(item))
    plan = root.find(".//TestPlan")
    plan.set("testname", "Small P0 workload: 60/20/10/10 logical actions")
    plan.find("stringProp[@name='TestPlan.comments']").text = (
        "Each random choice is one logical action: 60% course, 20% download, 10% assignment view, "
        "10% logout/login cycle. The cycle emits multiple HTTP samples; percentages do not describe HTTP request counts. "
        "Submission writes are covered by the separate functional acceptance, not this load test.")
    destination = source.with_name("moodle-small.jmx")
    # The private SSM tunnel can leave stale idle HTTP connections after think time.
    # Measure fresh connections explicitly; do not hide failed requests with retries.
    for sampler in root.findall('.//HTTPSamplerProxy'):
        sampler.find("boolProp[@name='HTTPSampler.use_keepalive']").text = 'false'
    plan.find("stringProp[@name='TestPlan.comments']").text += (
        ' HTTP keep-alive is disabled for the SSM tunnel; every request opens a fresh connection. No HTTP retries.')
    ET.indent(root)
    tree.write(destination, encoding="utf-8", xml_declaration=True)
    print(destination)


if __name__ == "__main__":
    main()
