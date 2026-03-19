import streamlit as st
import requests
import re
import os

# ====================== 基础配置 ======================
# 页面配置
st.set_page_config(
    page_title="寒区隧道智能查询及稳定性判识系统", 
    page_icon="🚇", 
    layout="wide"
)

# 自定义样式（核心修改：侧边栏宽度+按钮颜色）
st.markdown("""
<style>
/* 1. 调窄左侧侧边栏宽度（默认≈300px，改为220px） */
[data-testid="stSidebar"] {
    width: 220px !important;
    min-width: 220px !important;
    max-width: 220px !important;
}

/* 2. 蓝色系按钮样式（保存按钮+折叠按钮） */
.stExpander > div:first-child {
    background-color: #e8f4f8 !important;
    border-radius: 8px !important;
}
.stButton > button {
    background-color: #165DFF !important;  /* 阿里云蓝 */
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 8px 16px !important;
}
.stButton > button:hover {
    background-color: #0E42D2 !important;  /* hover加深 */
    border: none !important;
}

/* 3. 优化输入框样式 */
.stTextInput > div > div > input {
    border-radius: 6px !important;
}
.stTextArea > div > div > textarea {
    border-radius: 6px !important;
    font-family: "Consolas", "Monaco", monospace !important;
}

/* 4. 聊天框优化 */
[data-testid="stChatMessage"] {
    border-radius: 8px !important;
    padding: 12px 16px !important;
}
</style>
""", unsafe_allow_html=True)

# 知识库文件配置
KNOWLEDGE_FILE = "knowledge_base.txt"

# 默认知识库内容
DEFAULT_KNOWLEDGE = """## 1. 寒区隧道冻害机理
冻害主要由水分、温度、围岩孔隙共同作用，冬季水分结冰膨胀，导致衬砌开裂、渗水、鼓包、路面隆起。

## 2. 常见冻害类型
衬砌冻胀开裂、挂冰、冰塞、排水系统冻结、路面冻胀翻浆、保温层失效。

## 3. 防寒保温措施
保温板、保温泄水孔、防寒门、电伴热、优化混凝土配合比。

## 4. 防寒长度计算公式
L = L0 + K × (T1 - T0)
L：总防寒长度；L0：基础长度；K：修正系数；T0：环境最低温；T1：临界温度。
"""

# ====================== 知识库核心函数 ======================
def load_knowledge_base():
    """加载知识库（无则创建）"""
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    else:
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            f.write(DEFAULT_KNOWLEDGE)
        return DEFAULT_KNOWLEDGE

def save_knowledge_base(content):
    """保存知识库"""
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    st.success("✅ 知识库保存成功！")

def retrieve_knowledge(question, knowledge_base):
    """检索相关知识"""
    paragraphs = knowledge_base.split('\n\n')
    relevant = []
    q_words = set(re.findall(r'\w+', question.lower()))
    for para in paragraphs:
        p_words = set(re.findall(r'\w+', para.lower()))
        if q_words & p_words:
            relevant.append(para)
    return '\n\n'.join(relevant) if relevant else knowledge_base

# ====================== API与计算函数 ======================
def call_qwen_api(api_key, prompt):
    """调用通义千问API"""
    headers = {
        "Authorization": f"Bearer {api_key}", 
        "Content-Type": "application/json"
    }
    data = {
        "model": "qwen-turbo",
        "input": {"messages": [{"role": "user", "content": prompt}]},
        "parameters": {"result_format": "message"}
    }
    try:
        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            headers=headers,
            json=data,
            timeout=30,
            verify=False
        )
        return resp.json()["output"]["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ API调用失败：{str(e)}"

def calculate_cold_length(params):
    """计算防寒长度"""
    try:
        K = params.get("K", 1.0)
        T0 = params.get("T0", -20)
        T1 = params.get("T1", 0.5)
        L0 = params.get("L0", 100)
        L = L0 + K * (T1 - T0)
        return f"""📊 防寒长度计算结果
• 修正系数K：{K}
• 环境最低温T0：{T0}℃
• 临界温度T1：{T1}℃
• 基础长度L0：{L0}m
✅ 计算总防寒长度：**{L:.2f}米**"""
    except:
        return "❌ 参数错误，请检查K、T0、T1、L0是否为数字"

def parse_calc_question(question):
    """解析计算类问题参数"""
    if "计算防寒长度" not in question:
        return None
    params = {}
    k_match = re.search(r'K[=：](\d+\.?\d*)', question)
    t0_match = re.search(r'T0[=：](-?\d+\.?\d*)', question)
    t1_match = re.search(r'T1[=：](\d+\.?\d*)', question)
    l0_match = re.search(r'L0[=：](\d+\.?\d*)', question)
    if k_match: params["K"] = float(k_match.group(1))
    if t0_match: params["T0"] = float(t0_match.group(1))
    if t1_match: params["T1"] = float(t1_match.group(1))
    if l0_match: params["L0"] = float(l0_match.group(1))
    return params

# ====================== 界面渲染 ======================
def main():
    # 加载知识库
    knowledge_base = load_knowledge_base()

    # 左侧侧边栏（极简版）
    with st.sidebar:
        st.subheader("🔑 API配置")
        api_key = st.text_input(
            "阿里云API Key", 
            type="password",
            label_visibility="collapsed"
        )
        
        # 折叠式知识库编辑按钮
        with st.expander("✏️ 编辑知识库", expanded=False):
            new_content = st.text_area(
                "编辑内容", 
                value=knowledge_base, 
                height=400,
                label_visibility="collapsed"
            )
            if st.button("💾 保存知识库"):
                save_knowledge_base(new_content)
                knowledge_base = new_content

    # 主界面标题
    st.title("寒区隧道智能问答系统")
    st.divider()

    # 聊天交互
    user_question = st.chat_input("请输入问题...")
    if user_question:
        # 显示用户问题
        with st.chat_message("user"):
            st.write(user_question)
        
        # 生成回答
        with st.chat_message("assistant"):
            # 优先处理计算类问题
            calc_params = parse_calc_question(user_question)
            if calc_params:
                result = calculate_cold_length(calc_params)
                st.markdown(result)
            else:
                # 知识类问题：检查API Key + 检索知识库 + 调用API
                if not api_key:
                    st.warning("⚠️ 请先在左侧输入阿里云API Key")
                else:
                    relevant_knowledge = retrieve_knowledge(user_question, knowledge_base)
                    prompt = f"请基于以下寒区隧道专业知识回答问题，要求准确、简洁：\n\n{relevant_knowledge}\n\n问题：{user_question}"
                    answer = call_qwen_api(api_key, prompt)
                    st.markdown(answer)

if __name__ == "__main__":
    main()