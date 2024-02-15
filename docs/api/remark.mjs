import fs from "fs";
import { remark } from "remark";
import { visit } from "unist-util-visit";

const remarkDirectives = () => {
    return transformer;

    function transformer(tree) {
        visit(tree, "heading", visitor);
        visit(tree, "link", visitor);
    }

    function visitor(node, index, parent) {
        if (node.depth === 4) {
            const firstChild = node.children[0];
            if (["note", "warning"].includes(firstChild?.value?.toLowerCase())) {
                handleNoteOrWarning(node, index, parent, firstChild);
            } else if (firstChild?.type === "emphasis") {
                handleEmphasis(node, firstChild);
            } else if (firstChild?.type !== "inlineCode") {
                handleInlineCode(node, firstChild);
            }
        } else if (node.depth === 3) {
            node.children.forEach((child) => {
                if (child.type === "text" || child.type === "emphasis") {
                    handleInlineCode(node, child);
                }
                if (child.type === "link") {
                    child.children.forEach((child) => {
                        if (child.type === "text") {
                            handleInlineCode(node, child);
                        }
                    });
                }
            });
        }
        if (node.type === "link") {
            node.url = node.url.replace(".md", "");
        }
    }

    function handleNoteOrWarning(node, index, parent, firstChild) {
        const type = firstChild.value.toLowerCase();
        parent.children.splice(index, 1);
        parent.children[index].children[0].value = `:::${type}\n${parent.children[index].children[0].value}`;

        const lastChildValue = parent.children[index].children.slice(-1)[0]?.value?.trim();
        if (lastChildValue?.endsWith(":") && parent.children[index + 1]?.type === "code") {
            parent.children[index].children.slice(-1)[0].value += "\n";
            parent.children[index].children.push(parent.children[index + 1]);
            parent.children.splice(index + 1, 1);
        }

        parent.children[index].children.push({ type: "text", value: "\n:::" });
    }

    function handleEmphasis(node, firstChild) {
        firstChild.children.forEach((child) => {
            if (child.type === "text") {
                child.type = "inlineCode";
                child.value = `${child.value?.trim()}{:python}`;
            }
        });

        node.children.slice(1).forEach((child) => {
            if (child.type === "text") {
                child.type = "inlineCode";
                child.value = `${child.value?.trim()}{:python}`;
            }
            if (child.type === "link") {
                child.children.forEach((child) => {
                    if (child.type === "text") {
                        child.type = "inlineCode";
                        child.value = `${child.value?.trim()}{:python}`;
                    }
                });
            }
        });
    }

    function handleInlineCode(node, firstChild) {
        node.children[0] = {
            type: "inlineCode",
            value: `${firstChild.value?.trim()}{:python}`,
        };
    }
};

const markdown = fs.readFileSync(process.argv[2]);

remark()
    .use(remarkDirectives)
    .process(markdown, (err, file) => {
        if (err) throw err;
        fs.writeFileSync(process.argv[2], String(file));
    });
