#!/bin/sh

create_api_doc() {
    make --directory ./docs/api html
}

remove_source_files() {
    git rm -r --cache .
}

commit_website_files() {
  git checkout --orphan api-doc
  create_api_doc
  remove_source_files
  git add docs
  git commit --message "Travis build: $TRAVIS_BUILD_NUMBER"
}

upload_files() {
  git remote add nf-core "https://$NF_CORE_BOT@github.com/nf-core/tools.git" > /dev/null 2>&1
  git push --force --quiet --set-upstream nf-core api-doc
}

commit_website_files
upload_files