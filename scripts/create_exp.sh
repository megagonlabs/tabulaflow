# The script accepts the following arguments:
# 1. The name of the model to run
# 2. The dataset to run the model on
# 3. (optional) The llm to use, if not provided, "openai/gpt-4o" will be used
if [ "$#" -ne 2 ] && [ "$#" -ne 3 ]; then
    echo "Usage: $0 <model> <dataset> [llm]"
    exit 1
fi

model=$1
dataset=$2
llm=${3:-"openai/gpt-4o"}

# if model="agent", set model to "sql_agent"
# if model="zero", set model to "simple_zero_shot"
if [ "$model" = "agent" ]; then
    model="sql_agent"
elif [ "$model" = "zero" ]; then
    model="simple_zero_shot"
fi

# First list all .sh scripts under exp/ and find the one with the highest number
# The filenames follow the format of <number>_abc_xyz.sh
files=$(find exp/ -type f -name "*.sh")
max_num=-1
for file in $files; do
    # Extract the base filename
    filename=$(basename "$file")

    # Use regex to match and extract the leading number
    if [[ "$filename" =~ ^([0-9]+)_.*\.sh$ ]]; then
        num=${BASH_REMATCH[1]}
        if ((num > max_num)); then
            max_num=$num
            max_file=$file
        fi
    fi
done

# get the last part of the llm string
llm_simplified=$(echo $llm | rev | cut -d'/' -f1 | rev)

exp_id=$(($max_num + 1))
exp_name="${exp_id}_${model}_${dataset}_${llm_simplified}"
exp_file="exp/${exp_name}.sh"

# Next, write the following script to the new file:
# set -e
#
# .venv/bin/python -u -m tabulaflow.run_model --model <model> --dataset <dataset> --llm <llm>  --result_dir output/<exp_id>_run_model/ --overwrite
# .venv/bin/python -u -m tabulaflow.evaluate --result_dir output/<exp_id>_run_model/

cat <<EOF >$exp_file
set -e

.venv/bin/python -u -m tabulaflow.run_model --model $model --dataset $dataset --llm $llm --result_dir output/${exp_name}/ --overwrite
.venv/bin/python -u -m tabulaflow.evaluate --result_json output/${exp_name}/result.json
EOF

echo "Created $exp_file with the following content:"
cat $exp_file
