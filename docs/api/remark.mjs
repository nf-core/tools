import fs from "fs";
import { remark } from "remark";
import { visit } from "unist-util-visit";

function remarkDirectives() {
    return transformer;

    function transformer(tree) {
        visit(tree, "heading", visitor);
        visit(tree, "link", visitor);
    }

    function visitor(node, index, parent) {
        if (node.depth === 4) {
            if (["note", "warning"].includes(node.children[0].value?.toLowerCase())) {
                const type = node.children[0].value.toLowerCase();
                parent.children.splice(index, 1);
                parent.children[index].children[0].value = `:::${type}\n${parent.children[index].children[0].value}`;
                // if second to list parent.children[index].children ends with ":", check if the next node is a code block, if so, add the code block as a child to the current node
                if (parent.children[index].children.slice(-1)[0]?.value?.trim().endsWith(":")) {
                    if (parent.children[index + 1].type === "code") {
                        parent.children[index].children.slice(-1)[0].value += "\n";
                        parent.children[index].children.push(parent.children[index + 1]);
                        parent.children.splice(index + 1, 1);
                    }
                }
                parent.children[index].children.push({ type: "text", value: "\n:::" });
            } else if (node.children[0].type === "emphasis") {
                node.children[0].children.map((child) => {
                    if (child.type === "text") {
                        child.type = "inlineCode";
                        child.value = child.value?.trim() + "{:python}";
                    }
                });
                // convert the rest of the heading to inline code
                node.children.slice(1).map((child) => {
                    if (child.type === "text") {
                        child.type = "inlineCode";
                        child.value = child.value?.trim() + "{:python}";
                    }
                    if (child.type === "link") {
                        child.children.map((child) => {
                            if (child.type === "text") {
                                child.type = "inlineCode";
                                child.value = child.value?.trim() + "{:python}";
                            }
                        });
                    }
                });
            } else if (node.children[0].type !== "inlineCode") {
                node.children[0] = {
                    type: "inlineCode",
                    value: node.children[0].value?.trim() + "{:python}",
                };
            }
        } else if (node.depth === 3) {
            node.children.map((child) => {
                if (child.type === "text") {
                    child.type = "inlineCode";
                    child.value = child.value?.trim() + "{:python}";
                }
                if (child.type === "link") {
                    child.children.map((child) => {
                        if (child.type === "text") {
                            child.type = "inlineCode";
                            child.value = child.value?.trim() + "{:python}";
                        }
                    });
                }
                if (child.type === "emphasis") {
                    child.children.map((child) => {
                        if (child.type === "text") {
                            child.type = "inlineCode";
                            child.value = child.value?.trim() + "{:python}";
                        }
                    });
                }
            });
        }
        if (node.type === "link") {
            node.url = node.url.replace(".md", "");
        }
    }
}

let markdown = fs.readFileSync(process.argv[2]);

remark()
    .use(remarkDirectives)
    .process(markdown, function (err, file) {
        if (err) throw err;
        fs.writeFileSync(process.argv[2], String(file));
    });
