import gradio as gr
import requests
from pathlib import Path

API_BASE = "http://127.0.0.1:8000/api/v1"

# 全局 Token
current_token = None
current_username = None


def login(username: str, password: str):
    global current_token, current_username
    try:
        resp = requests.post(
            f"{API_BASE}/auth/login",
            data={"username": username, "password": password},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            current_token = data["access_token"]
            current_username = username
            return f"✅ 登录成功！欢迎 {username}", True
        else:
            return f"❌ 登录失败: {resp.text}", False
    except Exception as e:
        return f"❌ 连接错误: {str(e)}", False


def upload_documents(files, collection_name: str):
    """上传文档"""
    global current_token
    if not current_token:
        return "请先登录", "状态: 未登录"

    try:
        headers = {"Authorization": f"Bearer {current_token}"}
        files_data = [("files", (file.name, open(file.name, "rb"), "application/octet-stream")) for file in files]

        resp = requests.post(
            f"{API_BASE}/ingest",
            files=files_data,
            data={"collection": collection_name},
            headers=headers,
            timeout=120
        )

        if resp.status_code == 200:
            return resp.json()["message"], "✅ 上传成功，正在后台处理..."
        else:
            return f"上传失败: {resp.text}", "❌ 上传失败"
    except Exception as e:
        return f"请求异常: {str(e)}", "❌ 请求失败"


def list_documents():
    """查看当前用户文档列表 - 返回 Markdown 格式"""
    global current_token, current_username
    if not current_token:
        return "⚠️ 请先登录"

    try:
        headers = {"Authorization": f"Bearer {current_token}"}
        resp = requests.get(f"{API_BASE}/documents", headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()

            if data.get("status") != "success":
                return f"❌ 接口返回错误: {data.get('message', '未知错误')}"

            count = data.get("documents_count", 0)
            docs_info = data.get("documents_info", {})

            if count == 0 or not docs_info:
                return f"**用户 {current_username}** 当前没有上传任何文档。"

            # 生成 Markdown 格式
            lines = [f"**用户 {current_username} 的文档列表**（共 **{count}** 个文件）\n"]
            for file_name, chunk_count in docs_info.items():
                lines.append(f"• **{file_name}** —— **{chunk_count}** 个文档块")

            return "\n".join(lines)

        else:
            return f"❌ 获取失败 ({resp.status_code}): {resp.text}"

    except Exception as e:
        return f"❌ 请求异常: {str(e)}"


def delete_single_document(file_name: str, collection: str = "default"):
    """删除指定文档"""
    global current_token
    if not current_token:
        return "请先登录"

    try:
        headers = {"Authorization": f"Bearer {current_token}"}
        resp = requests.delete(
            f"{API_BASE}/documents/{file_name}",
            params={"collection": collection},
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            return f"✅ 成功删除文件：{file_name}"
        else:
            return f"❌ 删除失败: {resp.text}"
    except Exception as e:
        return f"请求异常: {str(e)}"


def delete_all_documents(collection: str = "default"):
    """清空所有文档"""
    global current_token
    if not current_token:
        return "请先登录"

    try:
        headers = {"Authorization": f"Bearer {current_token}"}
        resp = requests.delete(
            f"{API_BASE}/documents",
            params={"collection": collection},
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            return f"✅ 已清空所有文档（{collection} 集合）"
        else:
            return f"❌ 清空失败: {resp.text}"
    except Exception as e:
        return f"请求异常: {str(e)}"


def run_ragas_evaluation():
    """带 Token 的 RAGAS 评估"""
    global current_token
    if not current_token:
        return "请先登录后再进行评估", "状态: 未登录"

    try:
        headers = {"Authorization": f"Bearer {current_token}"}
        response = requests.get(
            f"http://127.0.0.1:8000/ragas",
            headers=headers,
            timeout=300
        )

        if response.status_code == 200:
            data = response.json()


            # 生成详细 Markdown 显示
            markdown = f"<h3>RAGAS 评估报告 - 用户: {data.get('user')}</h3>\n"
            markdown += "<h4>整体平均指标</h4>\n"
            for k, v in data.get("summary", {}).items():
                markdown += f"<b>{k}</b>: {v:.4f}<br>"

            markdown += "<h4>详细评估结果</h4>\n"
            markdown += "<table border='1' style='border-collapse: collapse; width:100%;'>\n"
            markdown += "<tr><th>问题</th><th>答案</th><th>Faithfulness</th><th>Answer Relevancy</th><th>Context Precision</th><th>Context Recall</th></tr>\n"

            for item in data.get("detailed_results", []):
                markdown += f"<tr>"
                markdown += f"<td>{item['question']}</td>"
                markdown += f"<td>{item['answer'][:200]}...</td>"
                markdown += f"<td>{item['faithfulness']:.4f}</td>"
                markdown += f"<td>{item['answer_relevancy']:.4f}</td>"
                markdown += f"<td>{item['context_precision']:.4f}</td>"
                markdown += f"<td>{item['context_recall']:.4f}</td>"
                markdown += f"</tr>\n"

            markdown += "</table>"

            status_text = f"评估完成！共评估 {len(data.get('detailed_results', []))} 个问题"
            return markdown, status_text
        else:
            return f"<h3 style='color:red'>评估失败: {response.text}</h3>", "评估失败"

    except Exception as e:
        return f"**异常**: {str(e)}", "连接后端失败"


def run_full_evaluation(max_pairs: int = 6, top_k: int = 15, prompt: str = ""):
    """调用后端评估接口并显示 HTML 表格"""
    global current_token
    if not current_token:
        return "<h3 style='color: red;'>⚠️ 请先登录后再进行评估</h3>", "状态: 未登录"

    try:
        headers = {"Authorization": f"Bearer {current_token}"}

        response = requests.post(
            f"{API_BASE}/evaluate/full",
            headers=headers,
            json={
                "max_pairs_per_doc": max_pairs,
                "top_k": top_k,
                "prompt": prompt
            },
            timeout=3600  # 评估可能需要较长时间
        )

        if response.status_code == 200:
            data = response.json()

            # 直接使用后端返回的 html_table
            html_content = f"""
            <div style="margin: 20px 0;">
                <h3>✅ 评估完成 - 用户: {data.get('user', '未知')}</h3>
                <p><strong>QA 对数量:</strong> {data.get('qa_count', 0)}</p>

                <h4>整体指标总结</h4>
                <ul>
                    <li><strong>Faithfulness:</strong> {data['summary'].get('faithfulness', 0):.4f}</li>
                    <li><strong>Answer Relevancy:</strong> {data['summary'].get('answer_relevancy', 0):.4f}</li>
                    <li><strong>Context Precision:</strong> {data['summary'].get('context_precision', 0):.4f}</li>
                    <li><strong>Context Recall:</strong> {data['summary'].get('context_recall', 0):.4f}</li>
                </ul>

                <h4>详细评估表格</h4>
                {data.get('html_table', '<p>无表格数据</p>')}
            </div>
            """

            status_text = f"评估成功！共生成 {data.get('qa_count', 0)} 个 QA 对"
            return html_content, status_text

        else:
            error_msg = f"<h3 style='color: red;'>评估失败 ({response.status_code})</h3><p>{response.text}</p>"
            return error_msg, f"HTTP {response.status_code} 错误"

    except requests.exceptions.Timeout:
        return "<h3 style='color: orange;'>⏳ 请求超时（评估时间过长）</h3>", "超时"
    except Exception as e:
        error_html = f"<h3 style='color: red;'>请求异常</h3><p>{str(e)}</p>"
        return error_html, "连接异常"

def chat_with_rag(question: str):
    """带 Token 的查询"""
    global current_token
    if not current_token:
        return "请先登录", ""

    try:
        headers = {"Authorization": f"Bearer {current_token}"}
        resp = requests.post(
            f"{API_BASE}/query",
            json={"question": question, "debug": False},
            headers=headers,
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            answer = data.get("answer", "无答案")
            sources = "\n".join([f"• {s.get('file_name')} (score: {s.get('score'):.4f})"
                                 for s in data.get("sources", [])])
            return answer, sources if sources else "无来源"
        else:
            return f"错误 ({resp.status_code}): {resp.text}", ""
    except Exception as e:
        return f"请求失败: {str(e)}", ""


def plot_rag_metrics(csv_path):
    import pandas as pd
    import matplotlib.pyplot as plt
    df = pd.read_csv(csv_path)

    # 如果有时间列，建议排序
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp")

    plt.figure(figsize=(10, 5))

    # 四条线
    plt.plot(df.index, df["faithfulness"], label="faithfulness")
    plt.plot(df.index, df["answer_relevancy"], label="answer_relevancy")
    plt.plot(df.index, df["context_precision"], label="context_precision")
    plt.plot(df.index, df["context_recall"], label="context_recall")

    plt.xlabel("Index / Time")
    plt.ylabel("Score")
    plt.title("RAG Evaluation Metrics Over Time")
    plt.legend()
    plt.grid()

    return plt

# ====================== Gradio UI ======================
with gr.Blocks(title="SmartDocRAG 测试平台") as demo:
    gr.Markdown("# SmartDocRAG 测试与管理平台")

    # 登录区域
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 登录")
            username_input = gr.Textbox(label="用户名", value="admin")
            password_input = gr.Textbox(label="密码", type="password", value="admin123")
            login_btn = gr.Button("登录", variant="primary")
            login_status = gr.Textbox(label="登录状态", interactive=False)

    # 主功能区
    with gr.Tabs():
        with gr.Tab("单问题测试"):
            question_input = gr.Textbox(label="输入问题", lines=2, placeholder="例如：违反兵役法规，逃离部队，如何处理？")
            with gr.Row():
                chat_btn = gr.Button("查询", variant="primary")
                clear_btn = gr.Button("清空")
            answer_output = gr.Textbox(label="答案", lines=8)
            sources_output = gr.Textbox(label="检索来源", lines=6)

        with gr.Tab("上传文档"):
            file_input = gr.File(label="选择文件（支持 PDF、DOCX、TXT、MD）", file_count="multiple")
            collection_input = gr.Textbox(label="集合名称（可选）", value="default")
            upload_btn = gr.Button("上传文档", variant="primary")
            upload_status = gr.Textbox(label="上传状态")

        with gr.Tab("文档管理"):
            with gr.Row():
                list_btn = gr.Button("刷新文档列表", variant="primary")
                list_output = gr.Markdown(label="文档列表", value="点击“刷新文档列表”查看")

            with gr.Row():
                delete_file_input = gr.Textbox(label="要删除的文件名（精确匹配）",
                                               placeholder="例如：中华人民共和国刑法_20201226.docx")
                delete_btn = gr.Button("删除指定文件", variant="secondary")

            with gr.Row():
                delete_all_btn = gr.Button("⚠️ 清空所有文档", variant="stop")

            delete_status = gr.Textbox(label="操作状态", interactive=False)

        with gr.Tab("RAGAS 评估"):
            eval_btn = gr.Button("开始 RAGAS 批量评估", variant="primary", size="large")
            eval_output = gr.Markdown(label="评估结果")
            eval_status = gr.Textbox(label="状态")

        with gr.Tab("RAG 评估闭环"):
            gr.Markdown("### 一键完整评估闭环（QA生成 + RAGAS评估）")

            with gr.Row():
                max_pairs_slider = gr.Slider(
                    label="每个文档生成 QA 对数量",
                    minimum=3,
                    maximum=12,
                    value=6,
                    step=1
                )
                top_k_slider = gr.Slider(
                    label="Top K值",
                    minimum=1,
                    maximum=30,
                    value=15,
                    step=1
                )
                prompt_input = gr.Textbox(
                    label="Prompt",
                    placeholder="""你是一个严格、准确的 Python 技术文档助手。

                    核心规则（必须绝对遵守）：
                    1. **只使用提供的上下文中的信息**回答问题，绝不允许使用任何外部知识、常识或预训练记忆进行补充。
                    2. 如果提供的上下文无法直接、明确地回答问题，必须**直接回复**：“根据提供的 Python 文档，无法找到相关答案。”
                    3. 绝不允许进行任何形式的推测、脑补、扩展或合理化。
                    4. 回答时优先引用具体的函数名、类名、模块、参数和代码示例。
                    5. 如果上下文中有代码示例，可以引用，但不能修改或补充。
                    
                    回答格式要求：
                    - 如果能回答：直接给出答案 + 引用来源
                    - 如果不能回答：只回复“根据提供的 Python 文档，无法找到相关答案。”，不要添加任何其他内容。
                    
                    请严格遵守以上规则，这是最高优先级。
                    """,
                    lines=8,                    # ← 设置行数，建议 6~12 行
                    max_lines=20,               # 最大显示行数
                    interactive=True)
                full_eval_btn = gr.Button("🚀 开始完整评估", variant="primary", size="large")

            # 使用 gr.HTML 显示后端返回的 html_table
            full_eval_html_output = gr.HTML(label="评估结果", value="<p>点击按钮开始评估</p>")
            full_eval_status = gr.Textbox(label="状态信息", interactive=False)
        # 👇 新增的评估 Tab
        with gr.Tab("历史结果"):
            gr.Markdown("### RAGAS 历史评估结果")

            plot_btn = gr.Button("刷新图表")
            plot_output = gr.Plot()

            plot_btn.click(
                fn=lambda: plot_rag_metrics("history_result.csv"),
                outputs=plot_output
            )

    # ====================== 事件绑定 ======================

    login_btn.click(
        login,
        inputs=[username_input, password_input],
        outputs=[login_status]
    )

    chat_btn.click(
        chat_with_rag,
        inputs=question_input,
        outputs=[answer_output, sources_output]
    )

    upload_btn.click(
        upload_documents,
        inputs=[file_input, collection_input],
        outputs=[upload_status]
    )

    list_btn.click(
        list_documents,
        outputs=list_output
    )

    delete_btn.click(
        delete_single_document,
        inputs=[delete_file_input],
        outputs=delete_status
    )

    delete_all_btn.click(
        delete_all_documents,
        outputs=delete_status
    )

    eval_btn.click(
        run_ragas_evaluation,
        outputs=[eval_output, eval_status]
    )

    # 按钮事件绑定
    full_eval_btn.click(
        run_full_evaluation,
        inputs=[max_pairs_slider, top_k_slider, prompt_input],
        outputs=[full_eval_html_output, full_eval_status]
    )

    clear_btn.click(lambda: ("", ""), outputs=[answer_output, sources_output])

    gr.Markdown("---\n**提示**：请先登录后再使用其他功能")

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )