"""
LangGraphの構造を視覚化するためのスクリプト
"""

import os
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをPYTHONPATHに追加
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_dir))

# LangGraphのインポート
from app.services.langgraph_processor import AgentState


def main():
    """
    LangGraphの構造を視覚化する
    """
    print("LangGraphの構造を視覚化します...")

    # グラフを手動で構築（コンパイル前のグラフを取得するため）
    from langgraph.graph import StateGraph, END

    # ノードの定義（簡略化のため、実際の関数は使用せず、ダミー関数を使用）
    def dummy_node(state):
        return state

    # グラフの構築
    workflow = StateGraph(AgentState)

    # ノードの追加
    workflow.add_node("parse_input", dummy_node)
    workflow.add_node("retrieve_context", dummy_node)
    workflow.add_node("use_tools", dummy_node)
    workflow.add_node("generate_response", dummy_node)
    workflow.add_node("update_chat_history", dummy_node)

    # エッジの定義
    workflow.set_entry_point("parse_input")
    workflow.add_edge("parse_input", "retrieve_context")

    # 条件付きエッジの定義
    def should_use_tools(state):
        # ダミーの条件関数
        return "use_tools"

    workflow.add_conditional_edges(
        "retrieve_context",
        should_use_tools,
        {"use_tools": "use_tools", "generate_response": "generate_response"},
    )

    workflow.add_edge("use_tools", "update_chat_history")
    workflow.add_edge("generate_response", "update_chat_history")
    workflow.add_edge("update_chat_history", END)

    # グラフを視覚化して保存
    try:
        # Graphvizがインストールされているか確認
        import graphviz

        # 最新のLangGraphバージョンでは、to_graphvizメソッドを使用
        try:
            # 新しいバージョン
            if hasattr(workflow, "to_graphviz"):
                graph_viz = workflow.to_graphviz()
            # 古いバージョン
            elif hasattr(workflow, "get_graph") and hasattr(workflow.get_graph(), "draw_graphviz"):
                graph_viz = workflow.get_graph().draw_graphviz()
            else:
                raise AttributeError("LangGraphのビジュアライゼーションメソッドが見つかりません")

            # 画像として保存
            output_path = os.path.join(root_dir, "graph_visualization")
            graph_viz.render(output_path, format="png", cleanup=True)
            print(f"グラフの視覚化が完了しました。画像は {output_path}.png に保存されました。")

            # DOT形式でも保存
            dot_path = os.path.join(root_dir, "graph_structure.dot")
            with open(dot_path, "w") as f:
                f.write(graph_viz.source)
            print(f"グラフ構造が {dot_path} に保存されました。")

        except AttributeError as e:
            print(f"LangGraphのビジュアライゼーションメソッドが見つかりません: {e}")
            print("代替方法として、DOT形式でグラフ構造を直接出力します...")

            # 代替方法：DOTファイルを直接生成
            dot_content = """
            digraph G {
                rankdir=LR;
                node [shape=box, style=filled, color=lightblue];
                
                START [shape=oval, color=green];
                END [shape=oval, color=red];
                
                START -> parse_input;
                parse_input -> retrieve_context;
                retrieve_context -> use_tools [label="use_tools"];
                retrieve_context -> generate_response [label="generate_response"];
                use_tools -> update_chat_history;
                generate_response -> update_chat_history;
                update_chat_history -> END;
            }
            """

            dot_path = os.path.join(root_dir, "graph_structure.dot")
            with open(dot_path, "w") as f:
                f.write(dot_content)
            print(f"グラフ構造が {dot_path} に保存されました。")

            # DOTファイルからPNG画像を生成
            try:
                g = graphviz.Source(dot_content)
                output_path = os.path.join(root_dir, "graph_visualization")
                g.render(output_path, format="png", cleanup=True)
                print(f"グラフの視覚化が完了しました。画像は {output_path}.png に保存されました。")
            except Exception as render_error:
                print(f"画像の生成中にエラーが発生しました: {render_error}")
                print("DOTファイルを手動でGraphvizツールで開いて視覚化してください。")

    except Exception as e:
        print(f"グラフの視覚化中にエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
