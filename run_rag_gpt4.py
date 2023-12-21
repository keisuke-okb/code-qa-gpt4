import os
import argparse
import glob
from tqdm import tqdm
from openai import OpenAI


def main(args):
    client = OpenAI(
        api_key="YOUR_API_KEY",
    )

    target_ext_dict = {
        ".py": "python"
    }
    files = sorted([f for f in glob.glob(os.path.join(args.input_dir, '**/*'), recursive=True) 
            if os.path.splitext(os.path.basename(f))[1] in target_ext_dict.keys()
            ])
    
    if not args.recursive:
        files = [f for f in files
                if not "\\" in str(f).replace(os.path.join(args.input_dir, ""), "")
                ]
        
    # rel_files = [str(f).replace(os.path.join(args.input_dir, ""), "") for f in files]
    summary_path = os.path.join(args.input_dir, "summary.txt")
    
    if not os.path.exists(summary_path):
        print(f"Target files count: {len(files)}")
        print(files)
        input("Press enter key to continue.")
        
        abstracts = ""
        for file in tqdm(files):
            with open(file, "r", encoding="utf-8") as f:
                texts = "".join(f.readlines())

            if len(texts.replace(" ", "")) > args.min_length:

                abs_length = int(len(texts.replace(" ", "")) // 20 // 100 * 100)
                rel_path = str(file).replace(os.path.join(args.input_dir, ""), "")

                # GPT-4で要約する
                ext = target_ext_dict[os.path.splitext(os.path.basename(file))[1]]
                prompt = f"""以下は、{ext}のスクリプトです。どのような処理を行っているのか最大でも200字程度で簡潔に要約してください。
このプログラムだけでは具体的な処理が不明な場合は推測してください。
また、複数のクラスや関数が定義されている場合は、それぞれの処理内容を簡単にリストアップしてください。
```{ext}
{texts}
```
"""
                response = client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                        {"role": "user", "content": prompt}, 
                    ],
                    max_tokens=args.max_token,
                )
                summary = response.choices[0].message.content
                abstracts += f"【{rel_path}】\n{summary}\n\n\n"

                with open(os.path.join(args.input_dir, "response.txt"), "a", encoding="UTF-8") as f:
                    f.writelines(f"【{rel_path}】\n{summary}\n\n\n")

        with open(summary_path, "w", encoding="UTF-8") as f:
            f.writelines(abstracts)
    
    else:
        with open(summary_path, "r", encoding="UTF-8") as f:
            abstracts = "".join(f.readlines())

        prompt = f"""以下は、スクリプトのファイル一覧と処理の説明です。
下の質問に答えるために最も関連すると思われるファイルを、関連する順番に箇条書きでリストアップしてください。
理由や説明は必要なく、ファイル名の箇条書きのみ出力してください。

出力の例：
- hoge.py
- fuga/aaa/bbb.py
- piyo/ccc.py

----------

{abstracts}

----------
質問：{args.question}
"""
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                    {"role": "user", "content": prompt}, 
                ],
                max_tokens=args.max_token,
            )
        res = response.choices[0].message.content
        
        # ===========
        contents = ""
        count = 0
        for l in res.split("\n"):
            if "- " in l:
                file = l.strip().replace("- ", "")
                try:
                    with open(os.path.join(args.input_dir, file), "r", encoding="utf-8") as f:
                        texts = "".join(f.readlines())
                    
                    contents += f"【{file}】\n{texts}\n\n\n"
                    count += 1
                    if count == args.max_rag_files:
                        break
                except:
                    print(f"Failed to load: {file}")
        
        prompt = f"""あなたは、優秀なプログラマーアシスタントです。

以下は、プログラムのファイル名とその内容を並べたものです。
これらのプログラムをもとに、下の質問になるべく簡潔に答えてください。
----------

{contents}

----------
質問：{args.question}
"""
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                    {"role": "user", "content": prompt}, 
                ],
                max_tokens=args.max_token_qa,
            )
        res = response.choices[0].message.content
        print(res)

        with open(os.path.join(args.input_dir, "qa_history.txt"), "a", encoding="UTF-8") as f:
            f.writelines(f"Q: {args.question} \nA:{res}\n\n\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--question", type=str, required=True)
    parser.add_argument("--min_length", type=int, default=100)
    parser.add_argument("--max_token", type=int, default=500)
    parser.add_argument("--max_token_qa", type=int, default=1000)
    parser.add_argument("--max_rag_files", type=int, default=3)
    parser.add_argument("--recursive", action='store_true')
    args = parser.parse_args()
    main(args)


