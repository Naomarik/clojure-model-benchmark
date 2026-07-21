#!/usr/bin/env python3
"""Deterministic Clojure-flavored correctness eval for llama-server models.

The 33 tasks cover Clojure/ClojureScript web application patterns including
reitit routes, hiccup/reagent components, malli schemas, HoneySQL query maps,
Datomic/EDN data wrangling, and taoensso-style utilities. Each task has a
programmatic checker; Clojure code is executed with Babashka.

Runs at temperature 0 against an OpenAI-compatible /v1/chat/completions
endpoint. Writes results to results/eval_clojure_<label>.json.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
BB = os.environ.get("BB") or shutil.which("bb") or "bb"


def strip_fences(text: str) -> str:
    """Extract content of the first markdown code fence, or return stripped text."""
    m = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def run_bb(code: str, timeout: int = 15):
    """Run Clojure code via babashka; return (ok, stdout, stderr)."""
    try:
        p = subprocess.run(
            [BB, "-e", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode == 0, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return False, "", "timeout"


def clj_string_literal(s: str) -> str:
    """Encode a python string as a Clojure string literal."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------------------
# Checkers. Each takes the raw model response text and returns (passed, detail).
# ---------------------------------------------------------------------------

def check_bb_output(harness_fmt, expected_stdout):
    """Splice model code into a bb harness and compare stdout."""
    def check(resp):
        code = strip_fences(resp)
        ok, out, err = run_bb(harness_fmt.format(code=code))
        if not ok:
            last = err.strip().splitlines()[-1] if err.strip() else "nonzero exit"
            return False, f"bb failed: {last}"
        if out.strip() == expected_stdout:
            return True, "output matched"
        return False, f"expected {expected_stdout!r}, got {out.strip()!r}"
    return check


def check_edn_equal(expected_edn: str):
    """Parse the model's response as EDN and compare structurally (key order
    insensitive for maps) against the expected EDN form, via bb."""
    def check(resp):
        got = strip_fences(resp)
        harness = (
            "(require '[clojure.edn :as edn])\n"
            f"(println (= (edn/read-string {clj_string_literal(expected_edn)})\n"
            f"            (edn/read-string {clj_string_literal(got)})))"
        )
        ok, out, err = run_bb(harness)
        if not ok:
            last = err.strip().splitlines()[-1] if err.strip() else "nonzero exit"
            return False, f"EDN parse/compare failed: {last}"
        if out.strip() == "true":
            return True, "EDN equal"
        return False, f"EDN mismatch, got {got[:100]!r}"
    return check


def check_exact(expected):
    def check(resp):
        got = resp.strip().strip("`").strip()
        if got == expected:
            return True, "exact match"
        return False, f"expected {expected!r}, got {resp.strip()[:80]!r}"
    return check


TASKS = []


def task(name):
    def deco(fn):
        TASKS.append((name, *fn()))
        return fn
    return deco


# ---------------------------------------------------------------------------
# Write-a-function tasks (bb-executed)
# ---------------------------------------------------------------------------

@task("fn_remove_empty_vals")
def _():
    # Pattern: recursive removal of empty map values.
    prompt = (
        "Write a Clojure function `remove-empty-vals` that takes a map and "
        "removes every entry whose value is nil, an empty string, or an empty "
        "collection. Recurse into nested map values first; if a nested map "
        "becomes empty after cleaning, remove that entry too. Keep false and 0 "
        "and non-blank strings. Reply with only the code in one code block, "
        "no explanation."
    )
    harness = (
        "{code}\n"
        '(println (= (remove-empty-vals {{:a 1 :b nil :c "" :d [] :e {{:f nil}} :g {{:h 2}}}})'
        " {{:a 1 :g {{:h 2}}}}))\n"
        '(println (= (remove-empty-vals {{:x "" :y {{:z nil :w 3}} :k false}})'
        " {{:y {{:w 3}} :k false}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("fn_vec_insert")
def _():
    # Pattern: vector insertion with the subvec splice idiom.
    prompt = (
        "Write a Clojure function `(vec-insert coll pos itm)` that returns a "
        "vector with itm inserted at index pos (elements at pos and after are "
        "shifted right). coll may be any sequential collection. Reply with "
        "only the code in one code block."
    )
    harness = "{code}\n(println (vec-insert [1 2 3 4] 2 99))\n(println (vec-insert '(:a :b) 0 :x))"
    return prompt, check_bb_output(harness, "[1 2 99 3 4]\n[:x :a :b]")


@task("fn_pluralize")
def _():
    # Pattern: simple count-based pluralization.
    prompt = (
        "Write a Clojure function `(pluralize word count)` that returns word "
        "unchanged when count is exactly 1, otherwise returns word with an "
        '"s" suffix appended. Reply with only the code in one code block.'
    )
    harness = '{code}\n(println (pluralize "car" 1) (pluralize "car" 3) (pluralize "part" 0))'
    return prompt, check_bb_output(harness, "car cars parts")


@task("fn_ago_str")
def _():
    # Pattern: relative-time condition ladder over quot.
    prompt = (
        "Write a Clojure function `(ago-str delta)` taking a duration in "
        "milliseconds and returning a relative-time string. Compute "
        "seconds/minutes/hours/days with (quot delta 1000), (quot delta 60000), "
        "(quot delta 3600000), (quot delta 86400000), then return the first "
        "match of: days > 1 -> \"N days ago\"; days = 1 -> \"1 day ago\"; "
        "hours = 1 -> \"1 hour ago\"; hours > 1 -> \"N hours ago\"; "
        "minutes >= 2 -> \"N minutes ago\"; minutes >= 1 -> \"1 minute ago\"; "
        "seconds > 1 -> \"N secs ago\"; otherwise \"Just now\". N is the "
        "computed integer. Reply with only the code in one code block."
    )
    harness = (
        "{code}\n(println (ago-str 180000))\n(println (ago-str 7200000))\n"
        "(println (ago-str 90000000))\n(println (ago-str 500))"
    )
    return prompt, check_bb_output(harness, "3 minutes ago\n2 hours ago\n1 day ago\nJust now")


@task("fn_keywordize_path")
def _():
    # Pattern: translation key path to dotted keyword.
    prompt = (
        "Write a Clojure function `keywordize` that takes either a keyword "
        "(returned unchanged) or a collection of keywords, and joins the "
        "collection's keyword names with \".\" into a single keyword, e.g. "
        "[:forms :new-request] -> :forms.new-request. Reply with only the code "
        "in one code block."
    )
    harness = (
        "{code}\n(println (keywordize [:forms :new-request]) (keywordize :a) "
        "(keywordize [:validation :request :geo-location]))"
    )
    return prompt, check_bb_output(
        harness, ":forms.new-request :a :validation.request.geo-location"
    )


@task("fn_normalize_email")
def _():
    # Pattern: nil-safe email normalization with lowercase and trim.
    prompt = (
        "Write a Clojure function `normalize-email` that trims and lowercases "
        "an email string, and returns nil when given nil. Reply with only the "
        "code in one code block."
    )
    harness = '{code}\n(println (normalize-email "  Foo@Example.COM ") (normalize-email nil))'
    return prompt, check_bb_output(harness, "foo@example.com nil")


# ---------------------------------------------------------------------------
# Data-structure emission tasks (EDN-parsed, structural comparison via bb)
# ---------------------------------------------------------------------------

@task("ds_honeysql_select")
def _():
    # Pattern: HoneySQL analytics query maps.
    prompt = (
        "Emit a HoneySQL query map (plain EDN, do not require any library) "
        "for: select the columns id and email from the users table where "
        "email-verified? equals true, ordered by created-at descending, "
        "limit 10. Use exactly the keys :select, :from, :where, :order-by, "
        ":limit. :select is a vector of column keywords, :from is a vector of "
        "one table keyword, :where is [:= :email-verified? true], :order-by is "
        "a vector of [column direction] pairs like [[:created-at :desc]]. "
        "Reply with only the EDN map."
    )
    expected = (
        "{:select [:id :email] :from [:users] "
        ":where [:= :email-verified? true] "
        ":order-by [[:created-at :desc]] :limit 10}"
    )
    return prompt, check_edn_equal(expected)


@task("ds_hiccup_card")
def _():
    # Pattern: hiccup/reagent components with keyword class shorthand.
    prompt = (
        "Write the hiccup (plain EDN vector) for: a div with CSS class "
        '"card" containing first an h2 with text "Pricing" and then a ul with '
        'two li children with texts "Basic" and "Pro". Use keyword class '
        "shorthand (:div.card). No attribute maps. Reply with only the EDN "
        "vector."
    )
    expected = '[:div.card [:h2 "Pricing"] [:ul [:li "Basic"] [:li "Pro"]]]'
    return prompt, check_edn_equal(expected)


@task("ds_malli_user_schema")
def _():
    # Pattern: Malli :map schemas.
    prompt = (
        "Write a malli :map schema (plain EDN vector, no library needed) for "
        "a user with entries in exactly this order: :user/email of type "
        ":string, :user/age of type :int, and :user/bio of type :string which "
        "is optional (use the {:optional true} properties map). Reply with "
        "only the EDN vector."
    )
    expected = "[:map [:user/email :string] [:user/age :int] [:user/bio {:optional true} :string]]"
    return prompt, check_edn_equal(expected)


# ---------------------------------------------------------------------------
# Code-fix tasks (bb-executed)
# ---------------------------------------------------------------------------

@task("fix_submap")
def _():
    # Pattern: submap checking with the select-keys equality idiom.
    prompt = (
        "This Clojure function should return true when map2 is a submap of "
        "map1 (every key/value pair of map2 appears in map1), but it has a "
        "bug. Fix it and reply with only the corrected code in one code "
        "block:\n\n"
        "```clojure\n"
        "(defn submap? [map1 map2]\n"
        "  (and (map? map1)\n"
        "       (map? map2)\n"
        "       (= (select-keys map2 (keys map1)) map2)))\n"
        "```"
    )
    harness = (
        "{code}\n"
        "(println (submap? {{:a 1 :b 2}} {{:a 1}}) "
        "(submap? {{:a 1}} {{:a 1 :b 2}}) "
        "(submap? {{:a 1}} {{:a 2}}))"
    )
    return prompt, check_bb_output(harness, "true false false")


@task("fix_update_if_exists")
def _():
    # Pattern: guarding before update.
    prompt = (
        "This Clojure function should apply f to the value at key k only when "
        "k is present in the map, returning the map unchanged otherwise. It "
        "has a bug (it creates the key / calls f on nil when the key is "
        "missing). Fix it and reply with only the corrected code in one code "
        "block:\n\n"
        "```clojure\n"
        "(defn update-if-exists [m k f]\n"
        "  (update m k f))\n"
        "```"
    )
    harness = (
        "{code}\n"
        "(println (update-if-exists {{:a 1}} :a inc))\n"
        "(println (update-if-exists {{:a 1}} :b inc))"
    )
    return prompt, check_bb_output(harness, "{:a 2}\n{:a 1}")


# ---------------------------------------------------------------------------
# EDN/JSON transformation tasks
# ---------------------------------------------------------------------------

@task("edn_status_counts")
def _():
    # Pattern: reducing over vectors of namespaced-key entity maps.
    prompt = (
        "Given this EDN vector of request maps:\n\n"
        "[{:request/id 1 :request/status :open}\n"
        " {:request/id 2 :request/status :closed}\n"
        " {:request/id 3 :request/status :open}\n"
        " {:request/id 4 :request/status :pending}]\n\n"
        "Produce the EDN map from status keyword to how many requests have "
        "that status. Reply with only the EDN map."
    )
    return prompt, check_edn_equal("{:open 2 :closed 1 :pending 1}")


@task("json_config_to_edn")
def _():
    # Pattern: EDN service config with keywordized keys.
    prompt = (
        "Convert this JSON config to an EDN map with keyword keys (values "
        "keep their types; the array becomes a vector of strings):\n\n"
        '{"port": 3001, "debug": false, "origins": ["a.com", "b.com"]}\n\n'
        "Reply with only the EDN map."
    )
    return prompt, check_edn_equal('{:port 3001 :debug false :origins ["a.com" "b.com"]}')


# ---------------------------------------------------------------------------
# Strict-format tasks
# ---------------------------------------------------------------------------

@task("strict_unused_binding")
def _():
    # Pattern: clj-kondo-style lint diagnosis of let bindings in ring handlers
    # (handler fns like app.auth.handlers / app.routes.handlers)
    prompt = (
        "clj-kondo would flag one unused binding in this Ring handler:\n\n"
        "```clojure\n"
        "(defn handle-login [req]\n"
        "  (let [email (get-in req [:params :email])\n"
        "        password (get-in req [:params :password])\n"
        "        session (:session req)]\n"
        "    (find-user email password)))\n"
        "```\n\n"
        "Reply with only the name of the unused binding, nothing else."
    )
    return prompt, check_exact("session")


@task("strict_ring_response_edn")
def _():
    # Pattern: Ring response maps returned from reitit handlers.
    prompt = (
        "Emit the Ring response map (plain EDN) for a 404 with plain-text "
        'body "Not Found". Use exactly the keys :status, :headers, :body; '
        ':headers is a map with the string key "Content-Type" set to '
        '"text/plain". Reply with only the EDN map, no code fence needed, '
        "nothing else."
    )
    expected = '{:status 404 :headers {"Content-Type" "text/plain"} :body "Not Found"}'
    return prompt, check_edn_equal(expected)


@task("edn_route_names")
def _():
    # Pattern: reitit route vectors with :name in route-data maps.
    prompt = (
        "Given this reitit route tree:\n\n"
        '["" ["/" {:name :dashboard}]\n'
        '    ["/login" {:name :login}]\n'
        '    ["/gallery" {:name :gallery}]\n'
        '    ["/pricing" {:name :pricing}]]\n\n'
        "Emit the EDN vector of all :name keywords sorted alphabetically by "
        "name. Reply with only the EDN vector."
    )
    return prompt, check_edn_equal("[:dashboard :gallery :login :pricing]")


# ---------------------------------------------------------------------------
# Context-augmented variants of the two failing tasks. In a coding-agent
# setting the model sees repository code as context; these prepend source
# snippets and reuse the same checkers.
# ---------------------------------------------------------------------------

@task("ctx_remove_empty_vals")
def _():
    # Same checker as fn_remove_empty_vals, with a representative helper shown
    # as project context.
    prompt = (
        "Here is existing code from the project "
        "(motorsaif/data_utils.cljc), showing the house style for "
        "recursive map-walking helpers:\n\n"
        "```clojure\n"
        "(defn present?\n"
        "  \"Return true if value is not empty or nil, works on non colls.\"\n"
        "  [v]\n"
        "  (if (coll? v)\n"
        "    (and (coll? v) (seq v))\n"
        "    (not (nil? v))))\n"
        "\n"
        "(defn update-if-exists [m k f & args]\n"
        "  (if (get-in m (ensure-vec k))\n"
        "    (apply update-in m (ensure-vec k) f args)\n"
        "    m))\n"
        "\n"
        "(defn deep-remove-empty-vals [data]\n"
        "  (walk/postwalk\n"
        "   (fn [i]\n"
        "     (if (map? i)\n"
        "       (remove-empty-pairs i) i))\n"
        "   data))\n"
        "```\n\n"
        "In the same style, write a Clojure function `remove-empty-vals` that "
        "takes a map and removes every entry whose value is nil, an empty "
        "string, or an empty collection. Recurse into nested map values "
        "first; if a nested map becomes empty after cleaning, remove that "
        "entry too. Keep false and 0 and non-blank strings. The code must be "
        "self-contained (define any helpers you use). Reply with only the "
        "code in one code block, no explanation."
    )
    harness = (
        "{code}\n"
        '(println (= (remove-empty-vals {{:a 1 :b nil :c "" :d [] :e {{:f nil}} :g {{:h 2}}}})'
        " {{:a 1 :g {{:h 2}}}}))\n"
        '(println (= (remove-empty-vals {{:x "" :y {{:z nil :w 3}} :k false}})'
        " {{:y {{:w 3}} :k false}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("ctx_malli_user_schema")
def _():
    # Same checker as ds_malli_user_schema, with representative Malli schemas
    # demonstrating [:key {:optional true} :type] entry syntax.
    prompt = (
        "Here is existing code from the project (rakibadesigns), showing how "
        "malli :map schemas are written:\n\n"
        "```clojure\n"
        ";; app.auth.middleware\n"
        "(def CurrentUser\n"
        "  \"Schema for current user injected into request.\"\n"
        "  [:map\n"
        "   [:user/id :uuid]\n"
        "   [:user/email :string]\n"
        "   [:user/verified :boolean]\n"
        "   [:user/admin? {:optional true} :boolean]])\n"
        "\n"
        ";; app.llm.prompts\n"
        "(def PromptContext\n"
        "  [:map\n"
        "   [:has-image-description? {:optional true} :boolean]\n"
        "   [:brand-name {:optional true} [:maybe :string]]])\n"
        "\n"
        ";; app.session.db\n"
        "(def ProviderModelSelection\n"
        "  [:map\n"
        "   [:provider {:optional true} :keyword]\n"
        "   [:model :string]])\n"
        "```\n\n"
        "Following the same syntax, write a malli :map schema (plain EDN "
        "vector, no library needed) for a user with entries in exactly this "
        "order: :user/email of type :string, :user/age of type :int, and "
        ":user/bio of type :string which is optional (use the "
        "{:optional true} properties map). Reply with only the EDN vector."
    )
    expected = "[:map [:user/email :string] [:user/age :int] [:user/bio {:optional true} :string]]"
    return prompt, check_edn_equal(expected)


# ---------------------------------------------------------------------------
# Harder multi-step tasks (hard_*), grounded in real repo patterns.
# ---------------------------------------------------------------------------

@task("hard_require_auth_handler")
def _():
    # Pattern: authentication middleware returning 401/404/200 Ring responses
    # with ownership checks.
    prompt = (
        "Write a Clojure function `(handle-get-design db req)` for a "
        "Ring/reitit API. db is a map from design id (string) to design maps "
        "like {:design/id \"d1\" :design/owner 7 :design/title \"Logo\"}. "
        "req is a Ring request map that may contain :current-user (a map "
        "with :user/id, injected by auth middleware) and has the design id "
        "at [:path-params :id]. Behavior, checked in order:\n"
        "1. no :current-user -> {:status 401 :body {:error \"unauthorized\"}}\n"
        "2. design id not in db -> {:status 404 :body {:error \"not-found\"}}\n"
        "3. design's :design/owner differs from the user's :user/id -> the "
        "same 404 response (don't leak existence)\n"
        "4. otherwise -> {:status 200 :body design}\n"
        "Reply with only the code in one code block."
    )
    harness = (
        "{code}\n"
        '(def db {{"d1" {{:design/id "d1" :design/owner 7 :design/title "Logo"}}\n'
        '          "d2" {{:design/id "d2" :design/owner 9 :design/title "Banner"}}}})\n'
        '(println (= (handle-get-design db {{:path-params {{:id "d1"}}}})'
        ' {{:status 401 :body {{:error "unauthorized"}}}}))\n'
        '(println (= (handle-get-design db {{:current-user {{:user/id 7}} :path-params {{:id "d1"}}}})'
        ' {{:status 200 :body {{:design/id "d1" :design/owner 7 :design/title "Logo"}}}}))\n'
        '(println (= (handle-get-design db {{:current-user {{:user/id 7}} :path-params {{:id "d2"}}}})'
        ' {{:status 404 :body {{:error "not-found"}}}}))\n'
        '(println (= (handle-get-design db {{:current-user {{:user/id 7}} :path-params {{:id "nope"}}}})'
        ' {{:status 404 :body {{:error "not-found"}}}}))'
    )
    return prompt, check_bb_output(harness, "true\ntrue\ntrue\ntrue")


@task("hard_paginated_query")
def _():
    # Pattern: HoneySQL maps with conditional clauses and limit/offset paging.
    prompt = (
        "Write a Clojure function `(users-query opts)` that builds a "
        "HoneySQL query map (plain EDN, no library). opts has keys "
        ":verified? (boolean or absent), :search (string or absent), "
        ":page (1-based int), :per-page (int). The result always has "
        ":select [:id :email], :from [:users], :order-by "
        "[[:created-at :desc]], :limit per-page, and :offset "
        "(* (dec page) per-page). Include a :where key only when at least "
        "one filter is given: :where is a vector starting with :and, "
        "followed by [:= :email-verified? verified?] when :verified? is "
        "present (note: false counts as present), then "
        "[:like :email \"%<search>%\"] when :search is present, in that "
        "order. When no filters are given, the map has no :where key at "
        "all. Reply with only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(println (= (users-query {{:page 1 :per-page 20}})\n"
        "  {{:select [:id :email] :from [:users] :order-by [[:created-at :desc]] :limit 20 :offset 0}}))\n"
        "(println (= (users-query {{:verified? true :page 3 :per-page 10}})\n"
        "  {{:select [:id :email] :from [:users] :where [:and [:= :email-verified? true]]"
        " :order-by [[:created-at :desc]] :limit 10 :offset 20}}))\n"
        '(println (= (users-query {{:verified? false :search "gmail" :page 2 :per-page 5}})\n'
        '  {{:select [:id :email] :from [:users] :where [:and [:= :email-verified? false] [:like :email "%gmail%"]]'
        " :order-by [[:created-at :desc]] :limit 5 :offset 5}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue\ntrue")


@task("hard_nest_join_rows")
def _():
    # Pattern: turning flat SQL join rows into nested entity maps.
    prompt = (
        "Write a Clojure function `(nest-requests rows)` that turns flat SQL "
        "join rows into nested entities. Each row is a map with "
        ":request/id, :request/status, :offer/id, :offer/price; rows from a "
        "LEFT JOIN, so :offer/id may be nil when a request has no offers. "
        "Return a vector of request maps sorted by :request/id ascending, "
        "each {:request/id .. :request/status .. :request/offers [..]} where "
        ":request/offers is a vector of {:offer/id .. :offer/price ..} "
        "sorted by :offer/id ascending, and [] (empty vector) when the "
        "request has no offers. Reply with only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(def rows [{{:request/id 1 :request/status :open :offer/id 10 :offer/price 50}}\n"
        "           {{:request/id 1 :request/status :open :offer/id 11 :offer/price 65}}\n"
        "           {{:request/id 2 :request/status :closed :offer/id nil :offer/price nil}}])\n"
        "(println (= (nest-requests rows)\n"
        "  [{{:request/id 1 :request/status :open\n"
        "     :request/offers [{{:offer/id 10 :offer/price 50}} {{:offer/id 11 :offer/price 65}}]}}\n"
        "   {{:request/id 2 :request/status :closed :request/offers []}}]))\n"
        "(println (= (nest-requests [{{:request/id 5 :request/status :pending :offer/id 3 :offer/price 9}}])\n"
        "  [{{:request/id 5 :request/status :pending :request/offers [{{:offer/id 3 :offer/price 9}}]}}]))"
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("hard_hiccup_status_table")
def _():
    # Pattern: hiccup components generated with conditional classes.
    prompt = (
        "Write a Clojure function `(status-table reqs)` returning hiccup "
        "(plain EDN, no library). reqs is a seq of maps with :request/id "
        "(int) and :request/status (keyword). Return exactly:\n"
        "[:table.requests\n"
        " [:thead [:tr [:th \"ID\"] [:th \"Status\"]]]\n"
        " tbody]\n"
        "where tbody is [:tbody row1 row2 ...] with one row per request in "
        "input order. Each row is [:tr {:class c} [:td id-str] [:td "
        "status-name]] where c is \"row open\" when the status is :open and "
        "\"row\" otherwise, id-str is (str id), and status-name is (name "
        "status). With no requests, tbody is just [:tbody]. Reply with only "
        "the code in one code block."
    )
    harness = (
        "{code}\n"
        "(println (= (status-table [{{:request/id 1 :request/status :open}} {{:request/id 2 :request/status :closed}}])\n"
        "  [:table.requests\n"
        '   [:thead [:tr [:th "ID"] [:th "Status"]]]\n'
        "   [:tbody\n"
        '    [:tr {{:class "row open"}} [:td "1"] [:td "open"]]\n'
        '    [:tr {{:class "row"}} [:td "2"] [:td "closed"]]]]))\n'
        "(println (= (status-table [])\n"
        '  [:table.requests [:thead [:tr [:th "ID"] [:th "Status"]]] [:tbody]]))'
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("hard_day_buckets")
def _():
    # Pattern: pure millisecond date math for analytics day buckets.
    prompt = (
        "Write a Clojure function `(day-buckets timestamps)` that groups a "
        "collection of epoch-millisecond timestamps into UTC day buckets "
        "using pure integer math (no java.time). A timestamp t belongs to "
        "the bucket (* 86400000 (quot t 86400000)). Return a sorted map "
        "(use sorted-map) from bucket-start-ms to the count of timestamps "
        "in that bucket. An empty input returns an empty map. Reply with "
        "only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(println (= (day-buckets [100 86400001 86400002 172800000 50])"
        " {{0 2, 86400000 2, 172800000 1}}))\n"
        "(println (= (day-buckets []) {{}}))\n"
        "(println (= (day-buckets [259200000]) {{259200000 1}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue\ntrue")


@task("hard_flatten_dict")
def _():
    # Pattern: flattening nested translation dictionaries into dotted keywords.
    prompt = (
        "Write a Clojure function `(flatten-dict d)` for an i18n "
        "dictionary: d is a nested map whose keys are simple keywords and "
        "whose leaf values are strings. Return a flat map from dotted "
        "keyword paths to the leaf strings, joining nested keys' names with "
        "\".\", e.g. {:forms {:new-request \"New Request\"}} -> "
        "{:forms.new-request \"New Request\"}. Handle arbitrary nesting "
        "depth. Reply with only the code in one code block."
    )
    harness = (
        "{code}\n"
        '(println (= (flatten-dict {{:forms {{:new-request "New Request" :submit "Submit"}} :nav {{:home "Home"}}}})\n'
        '  {{:forms.new-request "New Request" :forms.submit "Submit" :nav.home "Home"}}))\n'
        '(println (= (flatten-dict {{:a {{:b {{:c "x"}}}} :d "y"}}) {{:a.b.c "x" :d "y"}}))'
    )
    return prompt, check_bb_output(harness, "true\ntrue")


# ---------------------------------------------------------------------------
# Additional agentic correctness cases covering important language and domain
# gaps not exercised above.
# ---------------------------------------------------------------------------

@task("hard_apply_user_patch")
def _():
    prompt = (
        "Write a Clojure function `(apply-user-patch user patch)`. Only the "
        "keys :user/name, :user/bio, and :user/admin? may be copied from "
        "patch into user. Copy an allowed key only when it is present in "
        "patch; an explicitly present nil clears the value and an explicitly "
        "present false must be retained. Ignore every other patch key. Reply "
        "with only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(def user {{:user/name \"Ada\" :user/bio \"math\" :user/admin? true :user/id 7}})\n"
        "(println (= (apply-user-patch user {{:user/bio nil :user/admin? false :ignored 1}})"
        " {{:user/name \"Ada\" :user/bio nil :user/admin? false :user/id 7}}))\n"
        "(println (= (apply-user-patch user {{:user/name \"Grace\"}})"
        " {{:user/name \"Grace\" :user/bio \"math\" :user/admin? true :user/id 7}}))\n"
        "(println (= (apply-user-patch user {{:ignored nil}}) user))"
    )
    return prompt, check_bb_output(harness, "true\ntrue\ntrue")


@task("hard_reitit_path_by_name")
def _():
    prompt = (
        "A canonical reitit route node has the form `[segment data & "
        "children]`, where segment is a string, data is a map, and every "
        "child has the same form. Write `(path-by-name routes target)` where "
        "routes is a sequence of route nodes. Recursively find the first node "
        "whose data map has :name equal to target and return the concatenation "
        "of its segment with all ancestor segments. Return nil when absent. "
        "Reply with only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(def routes [[\"/\" {{:name :home}}]\n"
        "             [\"/admin\" {{}}\n"
        "              [\"/users\" {{:name :admin/users}}]\n"
        "              [\"/projects\" {{}} [\"/:id\" {{:name :admin/project}}]]]])\n"
        "(println (path-by-name routes :home))\n"
        "(println (path-by-name routes :admin/users))\n"
        "(println (path-by-name routes :admin/project))\n"
        "(println (path-by-name routes :missing))"
    )
    return prompt, check_bb_output(harness, "/\n/admin/users\n/admin/projects/:id\nnil")


@task("hard_honeysql_boolean_tree")
def _():
    prompt = (
        "Write `(visible-designs-query opts)` returning a HoneySQL query map. "
        "opts always has :tenant-id and :user-id and may have "
        ":excluded-statuses, a non-empty vector. Return exactly {:select [:*] "
        ":from [:designs] :where W}. W is [:and [:= :tenant-id tenant-id] "
        "[:or [:= :public? true] [:= :owner-id user-id]]], followed, only "
        "when :excluded-statuses is present, by [:not [:in :status "
        "excluded-statuses]]. Preserve this exact nested expression shape. "
        "Reply with only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(println (= (visible-designs-query {{:tenant-id 4 :user-id 9}})\n"
        " {{:select [:*] :from [:designs]\n"
        "   :where [:and [:= :tenant-id 4] [:or [:= :public? true] [:= :owner-id 9]]]}}))\n"
        "(println (= (visible-designs-query {{:tenant-id 4 :user-id 9 :excluded-statuses [:deleted :spam]}})\n"
        " {{:select [:*] :from [:designs]\n"
        "   :where [:and [:= :tenant-id 4] [:or [:= :public? true] [:= :owner-id 9]]\n"
        "           [:not [:in :status [:deleted :spam]]]]}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("hard_malli_errors_to_tree")
def _():
    prompt = (
        "Write `(errors->tree errors)` for already-normalized Malli issue "
        "maps shaped {:in path-vector :message string}. Return a nested map "
        "following every path component, including integer components. Each "
        "leaf is a vector of all messages for that exact path in input order. "
        "An empty input returns {}. Reply with only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(def errors [{{:in [:user :email] :message \"invalid\"}}\n"
        "             {{:in [:addresses 0 :zip] :message \"required\"}}\n"
        "             {{:in [:user :email] :message \"blocked\"}}\n"
        "             {{:in [:addresses 1 :zip] :message \"too short\"}}])\n"
        "(println (= (errors->tree errors)\n"
        " {{:user {{:email [\"invalid\" \"blocked\"]}}\n"
        "   :addresses {{0 {{:zip [\"required\"]}} 1 {{:zip [\"too short\"]}}}}}}))\n"
        "(println (= (errors->tree []) {{}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("hard_deep_merge")
def _():
    prompt = (
        "Write `(deep-merge left right)` for two maps. When both values at a "
        "key are maps, merge them recursively. For every other conflict, the "
        "right value replaces the left, including nil, false, vectors, and "
        "sets. Keep keys found on only one side. Reply with only the code in "
        "one code block."
    )
    harness = (
        "{code}\n"
        "(println (= (deep-merge {{:a {{:b 1 :c 2}} :x 1 :keep false}}\n"
        "                         {{:a {{:b 9 :d 3}} :x nil :new []}})\n"
        " {{:a {{:b 9 :c 2 :d 3}} :x nil :keep false :new []}}))\n"
        "(println (= (deep-merge {{:a {{:b 1}} :v 1}} {{:a 7 :v {{:x 2}}}})"
        " {{:a 7 :v {{:x 2}}}}))\n"
        "(println (= (deep-merge {{}} {{:enabled false}}) {{:enabled false}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue\ntrue")


@task("fix_lazy_notification_effects")
def _():
    prompt = (
        "This function is intended to call notify! eagerly exactly once for "
        "each user in input order, discard notify!'s return values, and return "
        "nil. It currently performs no notifications because map is lazy. Fix "
        "it and reply with only the corrected code in one code block:\n\n"
        "```clojure\n"
        "(defn notify-users! [notify! users]\n"
        "  (map notify! users)\n"
        "  nil)\n"
        "```"
    )
    harness = (
        "{code}\n"
        "(def calls (atom []))\n"
        "(println (nil? (notify-users! #(do (swap! calls conj %) :sent) [:a :b :c])))\n"
        "(println (= @calls [:a :b :c]))\n"
        "(reset! calls [])\n"
        "(println (nil? (notify-users! #(swap! calls conj %) [])))\n"
        "(println (= @calls []))"
    )
    return prompt, check_bb_output(harness, "true\ntrue\ntrue\ntrue")


@task("hard_normalize_project_pull")
def _():
    prompt = (
        "Write `(normalize-project pulled)` for a Datomic-style pull result. "
        "Return exactly the project keys :project/id and :project/name plus "
        ":project/tasks. Source tasks are under reverse-reference key "
        ":task/_project and may be absent. Each output task contains exactly "
        ":task/id, :task/title, and :task/done?. Remove :db/id and all other "
        "attributes. Sort tasks by :task/id ascending and always return tasks "
        "as a vector, including [] when absent. Reply with only the code in "
        "one code block."
    )
    harness = (
        "{code}\n"
        "(def pulled {{:db/id 99 :project/id \"p1\" :project/name \"Launch\" :extra 7\n"
        "             :task/_project [{{:db/id 3 :task/id 2 :task/title \"Ship\" :task/done? false :x 1}}\n"
        "                             {{:db/id 2 :task/id 1 :task/title \"Plan\" :task/done? true}}]}})\n"
        "(println (= (normalize-project pulled)\n"
        " {{:project/id \"p1\" :project/name \"Launch\"\n"
        "   :project/tasks [{{:task/id 1 :task/title \"Plan\" :task/done? true}}\n"
        "                   {{:task/id 2 :task/title \"Ship\" :task/done? false}}]}}))\n"
        "(println (= (normalize-project {{:project/id \"p2\" :project/name \"Empty\" :db/id 4}})\n"
        " {{:project/id \"p2\" :project/name \"Empty\" :project/tasks []}}))"
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("fix_threading_pipeline")
def _():
    prompt = (
        "This Clojure function should select active users, extract their "
        "emails, sort the emails, and return a vector, but it uses the wrong "
        "threading macro. Fix it and reply with only the corrected code in one "
        "code block:\n\n"
        "```clojure\n"
        "(defn active-emails [users]\n"
        "  (-> users\n"
        "      (filter :active?)\n"
        "      (map :email)\n"
        "      sort\n"
        "      vec))\n"
        "```"
    )
    harness = (
        "{code}\n"
        "(println (= (active-emails [{{:email \"z@x\" :active? true}}\n"
        "                            {{:email \"a@x\" :active? false}}\n"
        "                            {{:email \"b@x\" :active? true}}]) [\"b@x\" \"z@x\"]))\n"
        "(println (= (active-emails []) []))"
    )
    return prompt, check_bb_output(harness, "true\ntrue")


@task("hard_reduce_until_match")
def _():
    prompt = (
        "Write `(first-matching pred coll)` using reduce and reduced. Return "
        "the first value for which pred is truthy, or nil when none matches. "
        "Reduction must stop immediately after the first match and must not "
        "realize later elements. Inputs in this task do not contain nil. Reply "
        "with only the code in one code block."
    )
    harness = (
        "{code}\n"
        "(def seen (atom []))\n"
        "(def xs (eduction (map (fn [x] (swap! seen conj x) x)) [1 2 3 4 5]))\n"
        "(println (= (first-matching #(= % 3) xs) 3))\n"
        "(println (= @seen [1 2 3]))\n"
        "(println (nil? (first-matching even? [1 3 5])))\n"
        "(println (= (first-matching #(= % false) [true false true]) false))"
    )
    return prompt, check_bb_output(harness, "true\ntrue\ntrue\ntrue")


# ---------------------------------------------------------------------------

def chat(url, model, prompt, max_tokens, timeout):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        obj = json.loads(resp.read().decode())
    msg = obj["choices"][0]["message"]
    content = msg.get("content") or ""
    # Strip <think> blocks if the model emits them inline.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8081")
    ap.add_argument("--label", required=True)
    ap.add_argument("--model", default="Qwen3.6-35B-A3B")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    results = []
    passed = 0
    print(f"Running {len(TASKS)} tasks against {args.url} (label={args.label})\n")
    for name, prompt, checker in TASKS:
        t0 = time.perf_counter()
        try:
            resp = chat(args.url, args.model, prompt, args.max_tokens, args.timeout)
            ok, detail = checker(resp)
        except Exception as e:  # noqa: BLE001
            resp = None
            ok, detail = False, f"request error: {type(e).__name__}: {e}"
        elapsed = time.perf_counter() - t0
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {name:<26} {elapsed:6.1f}s  {detail}")
        results.append(
            {
                "task": name,
                "passed": bool(ok),
                "detail": detail,
                "elapsed_s": elapsed,
                "response": resp,
            }
        )

    print(f"\nScore: {passed}/{len(TASKS)}")

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": args.label,
        "url": args.url,
        "model": args.model,
        "score": passed,
        "total": len(TASKS),
        "results": results,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"eval_clojure_{args.label}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
