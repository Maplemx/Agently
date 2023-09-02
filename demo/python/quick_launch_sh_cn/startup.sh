#!/bin/bash

py_command="python"

# ANSI颜色代码
BLUE='\033[34m'
NC='\033[0m' # 恢复默认颜色

# Step 1. 检测用户的 python 版本
echo -e "${BLUE}[Step 1. 检测当前 python 版本]${NC}"
echo ""
# 检查当前Python版本
if ! command -v python &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo "未找到 Python 或 Python3 命令，请先安装 Python。"
        exit 1
    else
        py_command="python3"
    fi
elif [ "$(python -c 'import sys; print(sys.version_info[0])')" -eq 2 ]; then
    # 如果当前Python版本为2.x，则尝试使用python3作为py_command
    py_command="python3"
else
    py_command="python"
fi
echo "[完成]"
echo ""

# Step 2. 引导用户配置
echo -e "${BLUE}[Step 2. 检查当前配置项]${NC}"
echo ""
# 检查是否已存在 private_settings 文件
SETTINGS_FILE="private_settings"

if [ -f "$SETTINGS_FILE" ]; then
    echo "配置项存在，开始加载..."
    echo "如果希望重新配置，可以将。/private_settings文件和./myenv文件夹删除后重新执行"
    # 从文件中读取 KEY 和 PROXY
    source "$SETTINGS_FILE"
else
    
    echo "请选择想要使用的模型":
    models=("GPT" "MiniMax")
    # 输出可选的模型列表
    for i in "${!models[@]}"; do
        echo "[$i]: ${models[$i]}"
    done
    echo ""
    # 引导用户选择
    while true; do
        read -p "请输入要选择的模型的数字编号： " choice

        # 检查用户输入是否为数字和是否在有效范围内
        if [[ "$choice" =~ ^[0-9]+$ && "$choice" -ge 0 && "$choice" -lt ${#models[@]} ]]; then
            selected_model="${models[$choice]}"
            break
        else
            echo "无效的选择，请重新输入。"
        fi
    done

    # 引导用户输入相关授权信息
    case "$selected_model" in
        "GPT") read -p "请输入 API-KEY: " api_key
               read -p "请输入转发请求API地址 (使用官方默认API地址无需输入): " llm_url
               read -p "如需使用Proxy 请输入代理设置 (格式: http://xxx.xxx.xxx.xxx:1234，不使用无需输入): " proxy
               # 将模型名称写入配置文件
               echo "llm_name='$selected_model'" >> "$SETTINGS_FILE"
               # 检查用户输入的 API-KEY 是否有值
               if [ -n "$api_key" ]; then
                   # 将 KEY 写入配置文件
                   echo "api_key='$api_key'" >> "$SETTINGS_FILE"
               else
                   echo "输入的 API-KEY 为空。"
                   exit 1
               fi

               # 检查用户输入的 转发地址 是否有值
               if [ -n "$llm_url" ]; then
                   # 将 代理 写入配置文件
                   echo "llm_url='$llm_url'" >> "$SETTINGS_FILE"
               fi
               # 检查用户输入的 PROXY 是否有值
               if [ -n "$proxy" ]; then
                   # 将 代理 写入配置文件
                   echo "proxy='$proxy'" >> "$SETTINGS_FILE"
               fi
               ;;
        "MiniMax") read -p "请输入 Group-Id: " group_id
                   read -p "请输入 API-KEY: " api_key
                   # 将模型名称写入配置文件
                   echo "llm_name='$selected_model'" >> "$SETTINGS_FILE"
                   # 检查用户输入的 Group-Id 是否有值
                   if [ -n "$group_id" ]; then
                       # 将 Group-Id 写入配置文件
                       echo "group_id='$group_id'" >> "$SETTINGS_FILE"
                   else
                       echo "输入的 Group-Id 为空。"
                       exit 1
                   fi
                   # 检查用户输入的 API-KEY 是否有值
                   if [ -n "$api_key" ]; then
                       # 将 KEY 写入配置文件
                       echo "api_key='$api_key'" >> "$SETTINGS_FILE"
                   else
                       echo "输入的 API-KEY 为空。"
                       exit 1
                   fi
                   ;;
    esac
fi
echo "[完成]"
echo ""

# Step 3. 初始化虚拟环境和依赖
echo -e "${BLUE}[Step 3. 初始化环境]${NC}"
echo ""
# 检查虚拟环境目录是否存在，如果不存在则创建
if [ ! -d "myenv" ]; then
    $py_command -m venv myenv
fi

# 激活虚拟环境
source myenv/bin/activate  &> /dev/null

# 安装 Agently 包及相关依赖
pip install Agently  &> /dev/null
pip install pyyaml  &> /dev/null
pip install aiohttp  &> /dev/null
pip install python-dotenv  &> /dev/null

echo "[完成]"
echo ""

# Step 4. 选择要执行的文件
echo -e "${BLUE}[Step 4. 选择要执行的示例]${NC}"
echo ""

# 列出目录下所有的.py文件
files=($(find ./examples -type f -name "*.py"))

# 如果没有找到.py文件，则退出
if [ ${#files[@]} -eq 0 ]; then
    echo "未找到任何.py文件。"
    exit 1
fi

# 输出可选的.py文件列表
echo "==可选的示例文件：=="
for i in "${!files[@]}"; do
    echo "[$i]: ${files[$i]}"
done

echo ""

# 引导用户选择一个文件
while true; do
    read -p "请输入要执行的示例数字编号： " choice

    # 检查用户输入是否为数字和是否在有效范围内
    if [[ "$choice" =~ ^[0-9]+$ && "$choice" -ge 0 && "$choice" -lt ${#files[@]} ]]; then
        selected_file="${files[$choice]}"
        break
    else
        echo "无效的选择，请重新输入。"
    fi
done

echo "[完成]"
echo ""

# Step 5. 执行指令
echo ""
echo -e "${BLUE}[Step 5. 开始执行示例：'${selected_file}' (ctrl + c 可退出对话)]${NC}"
echo ""
$py_command -c "import os; from dotenv import load_dotenv; load_dotenv('$SETTINGS_FILE')" && $py_command $selected_file


# 退出虚拟环境
deactivate
