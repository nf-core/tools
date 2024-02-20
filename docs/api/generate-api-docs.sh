#!/bin/bash

# allow --force option and also a --release option (which takes a release name, or "all")
force=false
releases=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -f | --force )
            force=true
            ;;
        -r | --release )
            shift
            releases+=("$1")
            ;;
        -o | --output )
            shift
            output_dir="$1"
            ;;
        * )
            echo "Invalid argument: $1"
            exit 1
            ;;
    esac
    shift
done


# Set the output directory if not set
if [[ -z "$output_dir" ]]; then
    output_dir="../src/content/tools/docs"
fi

# if no release is specified, use all releases
if [[ ${#releases[@]} -eq 0 ]]; then
    releases=($(git tag))
    # add 'dev' to the list of releases
    releases+=("dev")
fi

# Loop through each release
for release in "${releases[@]}"; do
    # Checkout the release
    git checkout "$release"
    echo "_________________________"
    echo "Generating docs for release: $release"
    echo "_________________________"
    git checkout docs/api
    pip install -r docs/api/requirements.txt --quiet
    # add the napoleon extension to the sphinx conf.py
    sed -i 's/^extensions = \[/extensions = \[\n    "sphinx_markdown_builder",/' docs/api/_src/conf.py

    # run docs/api/make_lint_md.py if it exists
    # if [[ -f "docs/api/make_lint_md.py" ]]; then
    #     python docs/api/make_lint_md.py
    # fi

    find nf_core -name "*.py" | while IFS= read -r file; do
        # echo "Processing $file"

        # replace ..tip:: with note in the python docstrings due to missing directive in the markdown builder
        sed -i 's/^\(\s*\)\.\. tip::/\1\.\. note::/g' "$file"

    done

    # fix syntax in lint/merge_markers.py
    sed -i 's/>>>>>>> or <<<<<<</``>>>>>>>`` or ``<<<<<<<``/g' nf_core/lint/merge_markers.py
    # remove markdown files if --force is set
    if [[ "$force" = true ]]; then
        echo -e "\n\e[31mRemoving $output_dir/$release because of '--force'\e[0m"
        rm -rf "$output_dir/$release"
    fi
    sphinx-build -b markdown docs/api/_src "$output_dir/$release"

    # undo all changes
    git restore .

    git checkout -
    # replace :::{seealso} with :::tip in the markdown files
    find "$output_dir/$release" -name "*.md" -exec sed -i 's/:::{seealso}/:::tip/g' {} \;
    i=1
    sp="/-\|" # spinner
    find "$output_dir/$release" -name "*.md" | while IFS= read -r file; do
        # echo "Processing $file"
        printf "\b${sp:i++%${#sp}:1}"
        node docs/api/remark.mjs "$file"
    done
    # remove empty files
    find "$output_dir/$release" -name "*.md" -size 0 -delete
    # remove `.doctrees` directory
    rm -rf "$output_dir/$release/.doctrees"
    # run pre-commit to fix any formatting issues on the generated markdown files
    pre-commit run --files "$output_dir/$release"
done
