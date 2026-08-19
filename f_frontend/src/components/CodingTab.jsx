import React, { useState, useEffect, useRef } from 'react';

const USER_COLORS = [
  "#3b82f6", // Blue (Anushka)
  "#10b981", // Emerald Green (Rahul)
  "#a855f7", // Purple (Aditi)
  "#f59e0b", // Amber (Rohan)
  "#ec4899", // Pink
  "#06b6d4", // Cyan
  "#f97316", // Orange
  "#84cc16"  // Lime
];

const getParticipantColor = (userId, name, idx = 0) => {
  const str = (userId || name || "user").toString();
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return USER_COLORS[Math.abs(hash + idx) % USER_COLORS.length];
};

const SmartCodeEditor = ({ value, onChange, lang, isRoomActive = false, participants = [], currentUserId = "" }) => {
  const textareaRef = useRef(null);
  const gutterRef = useRef(null);
  const videoRef = useRef(null);
  const screenStreamRef = useRef(null);

  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const [scrollTop, setScrollTop] = useState(0);
  const [isScreenSharing, setIsScreenSharing] = useState(false);

  // Extract active remote participants & assign unique color, name, line & col when isRoomActive is ON
  const remoteUsers = React.useMemo(() => {
    if (!isRoomActive || !Array.isArray(participants)) return [];
    const myId = String(currentUserId || localStorage.getItem("user_id") || "");
    return participants
      .filter(p => p && String(p.user_id) !== myId)
      .map((p, idx) => {
        const color = p.color || getParticipantColor(p.user_id, p.name || p.user_name, idx);
        let cursor = { line: 1, col: 1 };
        if (p.cursor && typeof p.cursor === 'object') {
          cursor = {
            line: Number(p.cursor.line || p.cursor.lineNumber || 1),
            col: Number(p.cursor.col || p.cursor.ch || p.cursor.column || 1)
          };
        }
        return {
          id: p.user_id || `remote_${idx}`,
          name: p.name || p.user_name || `Participant ${idx + 1}`,
          color: color,
          cursor: cursor,
          isEditing: Boolean(p.is_editing)
        };
      });
  }, [isRoomActive, participants, currentUserId]);

  const lines = (value || "").split("\n");
  const lineCount = lines.length;
  const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);

  const handleScroll = () => {
    if (textareaRef.current) {
      setScrollTop(textareaRef.current.scrollTop);
      if (gutterRef.current) {
        gutterRef.current.scrollTop = textareaRef.current.scrollTop;
      }
    }
  };

  const updateCursorInfo = () => {
    if (!textareaRef.current) return;
    const { selectionStart, value: val } = textareaRef.current;
    const textBeforeCursor = val.substring(0, selectionStart);
    const lineList = textBeforeCursor.split("\n");
    const currentLine = lineList.length;
    const currentCol = lineList[lineList.length - 1].length + 1;
    setCursorPos({ line: currentLine, col: currentCol });
  };

  const toggleScreenShare = async () => {
    if (!isScreenSharing) {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ 
          video: { displaySurface: 'browser' }, 
          audio: false,
          preferCurrentTab: false,
          surfaceSwitching: 'include'
        });
        screenStreamRef.current = stream;
        setIsScreenSharing(true);
        setTimeout(() => {
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
        }, 100);
        stream.getVideoTracks()[0].onended = () => {
          setIsScreenSharing(false);
          screenStreamRef.current = null;
        };
      } catch (e) {
        console.warn("Screen share cancelled or failed:", e);
      }
    } else {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
        screenStreamRef.current = null;
      }
      setIsScreenSharing(false);
    }
  };

  const handleKeyDown = (e) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const { selectionStart, selectionEnd, value: val } = textarea;

    if (e.key === "Tab") {
      e.preventDefault();
      if (selectionStart !== selectionEnd) {
        const startLineIdx = val.substring(0, selectionStart).split("\n").length - 1;
        const endLineIdx = val.substring(0, selectionEnd).split("\n").length - 1;
        const allLines = val.split("\n");
        if (e.shiftKey) {
          for (let i = startLineIdx; i <= endLineIdx; i++) {
            if (allLines[i].startsWith("  ")) allLines[i] = allLines[i].substring(2);
            else if (allLines[i].startsWith(" ")) allLines[i] = allLines[i].substring(1);
          }
        } else {
          for (let i = startLineIdx; i <= endLineIdx; i++) allLines[i] = "  " + allLines[i];
        }
        const newVal = allLines.join("\n");
        onChange(newVal);
        setTimeout(() => {
          textarea.selectionStart = Math.max(0, selectionStart + (e.shiftKey ? -2 : 2));
          textarea.selectionEnd = Math.max(0, selectionEnd + (allLines.length * (e.shiftKey ? -2 : 2)));
          updateCursorInfo();
        }, 0);
      } else {
        const newVal = val.substring(0, selectionStart) + "  " + val.substring(selectionEnd);
        onChange(newVal);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = selectionStart + 2;
          updateCursorInfo();
        }, 0);
      }
      return;
    }

    if (e.key === "Enter") {
      e.preventDefault();
      const currentLineText = val.substring(0, selectionStart).split("\n").pop() || "";
      const matchIndent = currentLineText.match(/^(\s*)/);
      let indent = matchIndent ? matchIndent[1] : "";
      
      const charBefore = val.charAt(selectionStart - 1);
      const charAfter = val.charAt(selectionStart);

      if (charBefore === "{" && charAfter === "}") {
        const extraIndent = indent + "  ";
        const newVal = val.substring(0, selectionStart) + "\n" + extraIndent + "\n" + indent + val.substring(selectionEnd);
        onChange(newVal);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = selectionStart + 1 + extraIndent.length;
          updateCursorInfo();
        }, 0);
        return;
      }

      if (charBefore === "{" || charBefore === ":" || charBefore === "(" || charBefore === "[") {
        indent += "  ";
      }

      const newVal = val.substring(0, selectionStart) + "\n" + indent + val.substring(selectionEnd);
      onChange(newVal);
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = selectionStart + 1 + indent.length;
        updateCursorInfo();
      }, 0);
      return;
    }

    const pairs = { "{": "}", "(": ")", "[": "]", '"': '"', "'": "'" };

    if (pairs[e.key]) {
      const closeChar = pairs[e.key];
      if ((e.key === '"' || e.key === "'") && val.charAt(selectionStart) === e.key) {
        e.preventDefault();
        textarea.selectionStart = textarea.selectionEnd = selectionStart + 1;
        updateCursorInfo();
        return;
      }

      e.preventDefault();
      if (selectionStart !== selectionEnd) {
        const selectedText = val.substring(selectionStart, selectionEnd);
        const newVal = val.substring(0, selectionStart) + e.key + selectedText + closeChar + val.substring(selectionEnd);
        onChange(newVal);
        setTimeout(() => {
          textarea.selectionStart = selectionStart + 1;
          textarea.selectionEnd = selectionEnd + 1;
          updateCursorInfo();
        }, 0);
      } else {
        const newVal = val.substring(0, selectionStart) + e.key + closeChar + val.substring(selectionEnd);
        onChange(newVal);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = selectionStart + 1;
          updateCursorInfo();
        }, 0);
      }
      return;
    }

    if (e.key === "Backspace" && selectionStart === selectionEnd && selectionStart > 0) {
      const prevChar = val.charAt(selectionStart - 1);
      const nextChar = val.charAt(selectionStart);
      if (
        (prevChar === "{" && nextChar === "}") ||
        (prevChar === "(" && nextChar === ")") ||
        (prevChar === "[" && nextChar === "]") ||
        (prevChar === '"' && nextChar === '"') ||
        (prevChar === "'" && nextChar === "'")
      ) {
        e.preventDefault();
        const newVal = val.substring(0, selectionStart - 1) + val.substring(selectionStart + 1);
        onChange(newVal);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = selectionStart - 1;
          updateCursorInfo();
        }, 0);
        return;
      }
    }
  };

  return (
    <div style={{
      position: "relative",
      display: "flex",
      flexDirection: "column",
      background: "#080c16",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: "14px",
      overflow: "hidden",
      boxShadow: "0 8px 32px rgba(0,0,0,0.5)"
    }}>
      {/* HEADER WITH CONDITIONAL SINGLE-USER VS MULTI-PARTICIPANT CURSOR STATUS */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 14px",
        background: "rgba(255,255,255,0.03)",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        fontSize: "11px",
        color: "#94a3b8",
        fontWeight: 700,
        flexWrap: "wrap",
        gap: "10px"
      }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: isRoomActive ? "#00e5c3" : "#64748b", boxShadow: isRoomActive ? "0 0 8px #00e5c3" : "none" }}></span>
          <span style={{ textTransform: "uppercase", letterSpacing: "0.5px", color: "#fff" }}>{lang || "code"} editor</span>

          {/* Case 1: Coding Room = OFF */}
          {!isRoomActive && (
            <span style={{
              background: "rgba(100,116,139,0.15)",
              border: "1px solid rgba(100,116,139,0.4)",
              color: "#94a3b8",
              padding: "2px 8px",
              borderRadius: "12px",
              fontSize: "10px",
              fontWeight: 700
            }}>
              👤 Single-User Mode (Local Edit)
            </span>
          )}
          
          {/* Case 2: Coding Room = ON -> Live Multi-Participant Cursor Indicators */}
          {isRoomActive && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
              {/* Local User Badge */}
              <span style={{
                background: "rgba(0,229,195,0.15)",
                border: "1px solid rgba(0,229,195,0.4)",
                color: "#00e5c3",
                padding: "2px 8px",
                borderRadius: "12px",
                fontSize: "10px",
                fontWeight: 800,
                display: "flex",
                alignItems: "center",
                gap: "4px"
              }}>
                <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: "#00e5c3" }}></span>
                👤 You: Ln {cursorPos.line}, Col {cursorPos.col}
              </span>

              {/* Remote Participant Badges with Unique Colors */}
              {remoteUsers.map(u => (
                <span key={u.id} style={{
                  background: `${u.color}22`,
                  border: `1px solid ${u.color}66`,
                  color: u.color,
                  padding: "2px 8px",
                  borderRadius: "12px",
                  fontSize: "10px",
                  fontWeight: 800,
                  display: "flex",
                  alignItems: "center",
                  gap: "4px"
                }}>
                  <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: u.color }}></span>
                  👤 {u.name}: Ln {u.cursor.line}, Col {u.cursor.col}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* FLOATING SCREEN SHARE PREVIEW IF ACTIVE */}
      {isScreenSharing && (
        <div style={{
          position: "absolute",
          top: "46px",
          right: "14px",
          zIndex: 100,
          background: "#0c1220",
          border: "1px solid #f59e0b",
          borderRadius: "10px",
          padding: "6px",
          boxShadow: "0 10px 30px rgba(0,0,0,0.8)",
          width: "210px"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px", fontSize: "10px", fontWeight: 800, color: "#fbbf24" }}>
            <span>🔴 Screen Share Active</span>
            <button onClick={toggleScreenShare} style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "10px" }}>✕ Stop</button>
          </div>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: "100%", height: "110px", borderRadius: "6px", objectFit: "cover", background: "#000" }}
          />
        </div>
      )}

      {/* CODE EDITOR CONTAINER WITH GUTTER & MULTI-USER CURSOR HIGHLIGHTS */}
      <div style={{ display: "flex", position: "relative", height: "360px" }}>
        {/* GUTTER LINE NUMBERS */}
        <div
          ref={gutterRef}
          style={{
            width: "52px",
            background: "rgba(0,0,0,0.4)",
            borderRight: "1px solid rgba(255,255,255,0.08)",
            padding: "12px 0",
            fontFamily: "'DM Mono', 'Fira Code', monospace",
            fontSize: "13px",
            lineHeight: "1.6",
            color: "rgba(255,255,255,0.3)",
            textAlign: "right",
            paddingRight: "8px",
            userSelect: "none",
            overflowY: "hidden",
            flexShrink: 0
          }}
        >
          {lineNumbers.map(n => {
            const isUserLine = n === cursorPos.line;
            const remoteOnLine = isRoomActive ? remoteUsers.filter(u => u.cursor.line === n) : [];
            let numColor = "rgba(255,255,255,0.3)";
            let fontWeight = 400;

            if (isUserLine) {
              numColor = "#00e5c3";
              fontWeight = 800;
            } else if (remoteOnLine.length > 0) {
              numColor = remoteOnLine[0].color;
              fontWeight = 800;
            }

            return (
              <div 
                key={n} 
                style={{
                  color: numColor,
                  fontWeight: fontWeight,
                  display: "flex",
                  justifyContent: "flex-end",
                  alignItems: "center",
                  gap: "2px"
                }}
              >
                {/* Render colored indicator dots for remote user cursors on line */}
                {remoteOnLine.map(ru => (
                  <span key={ru.id} style={{
                    display: "inline-block",
                    width: "5px",
                    height: "5px",
                    borderRadius: "50%",
                    background: ru.color
                  }} title={`${ru.name}'s cursor`} />
                ))}
                <span>{n}</span>
              </div>
            );
          })}
        </div>

        {/* TEXTAREA FOR EDITING */}
        <textarea
          ref={textareaRef}
          id="code-textarea"
          value={value}
          onChange={(e) => { onChange(e.target.value); updateCursorInfo(); }}
          onKeyDown={handleKeyDown}
          onKeyUp={updateCursorInfo}
          onClick={updateCursorInfo}
          onScroll={handleScroll}
          spellCheck="false"
          style={{
            flex: 1,
            height: "100%",
            background: "transparent",
            border: "none",
            outline: "none",
            color: "#f0f4fd",
            fontFamily: "'DM Mono', 'Fira Code', monospace",
            fontSize: "13px",
            lineHeight: "1.6",
            padding: "12px",
            resize: "none",
            tabSize: 2,
            whiteSpace: "pre",
            wordBreak: "normal"
          }}
          aria-label="Code editor"
        />

        {/* LIVE MULTI-PARTICIPANT FLOATING CURSORS & NAME TAGS (CASE 2: ROOM ON ONLY) */}
        {isRoomActive && remoteUsers.map(u => {
          const lineY = (u.cursor.line - 1) * 20.8 + 12 - scrollTop;
          const colX = Math.min(680, Math.max(0, (u.cursor.col - 1) * 7.8 + 64));
          const isVisible = lineY >= -15 && lineY <= 345;

          if (!isVisible) return null;

          return (
            <div key={u.id} style={{
              position: "absolute",
              top: `${lineY}px`,
              left: `${colX}px`,
              pointerEvents: "none",
              zIndex: 20,
              transition: "top 0.08s ease-out, left 0.08s ease-out"
            }}>
              {/* Vertical Caret Bar */}
              <div style={{
                width: "2px",
                height: "20px",
                background: u.color,
                boxShadow: `0 0 10px ${u.color}, 0 0 3px #fff`,
                position: "relative",
                borderRadius: "1px"
              }}>
                {/* Floating Name Badge Above Cursor */}
                <span style={{
                  position: "absolute",
                  top: "-20px",
                  left: "0px",
                  background: u.color,
                  color: "#fff",
                  fontSize: "9.5px",
                  fontWeight: 900,
                  padding: "2px 6px",
                  borderRadius: "4px 4px 4px 0",
                  whiteSpace: "nowrap",
                  boxShadow: `0 2px 8px ${u.color}66, 0 2px 4px rgba(0,0,0,0.5)`,
                  letterSpacing: "0.2px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px"
                }}>
                  <span>👤 {u.name}</span>
                  {u.isEditing && <span style={{ fontSize: "8px", opacity: 0.9 }}>✍️</span>}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const defaultCodeTemplates = {
  python: `def twoSum(nums, target):
    # Write your code here
    pass
`,
  javascript: `function twoSum(nums, target) {
    // Write your code here
    
}
`,
  typescript: `function twoSum(nums: number[], target: number): number[] {
    // Write your code here
    return [];
}
`,
  java: `class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Write your code here
        return new int[]{};
    }
}
`,
  cpp: `#include <vector>
using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        // Write your code here
        return {};
    }
};
`,
  csharp: `public class Solution {
    public int[] TwoSum(int[] nums, int target) {
        // Write your code here
        return new int[]{};
    }
}
`,
  go: `func twoSum(nums []int, target int) []int {
    // Write your code here
    return []int{}
}
`,
  rust: `impl Solution {
    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
        // Write your code here
        vec![]
    }
}
`,
  php: `function twoSum($nums, $target) {
    // Write your code here
    return [];
}
`,
  ruby: `def two_sum(nums, target)
    # Write your code here
end
`,
  swift: `class Solution {
    func twoSum(_ nums: [Int], _ target: Int) -> [Int] {
        // Write your code here
        return []
    }
}
`,
  kotlin: `class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        // Write your code here
        return intArrayOf()
    }
}
`,
  sql: `-- Write your SQL query here
SELECT * FROM table_name;
`
};

const getDynamicStarterCode = (problem, targetLang) => {
  if (!problem) return "";
  
  // 1. Check if problem already has starter_code for the language
  let starter = problem.starter_code || {};
  if (typeof starter === 'string') {
    try { starter = JSON.parse(starter); } catch(e) { starter = {}; }
  }
  if (starter[targetLang]) {
    return starter[targetLang];
  }
  
  // 2. Derive function name from problem_id slug or title
  let slug = (problem.problem_id || "solution").toLowerCase();
  
  // Determine problem type flags
  const isParentheses = slug.includes("parentheses");
  const isReverseString = slug.includes("reverse") && slug.includes("string");
  const isStock = slug.includes("stock");
  const isDuplicate = slug.includes("duplicate");
  const isProduct = slug.includes("product");
  const isSubarray = slug.includes("subarray");
  const is3Sum = slug.includes("3sum");
  const isSubstring = slug.includes("substring");
  const isBinarySearch = slug.includes("binary") && slug.includes("search") && !slug.includes("rotated");
  const isRotated = slug.includes("rotated");
  const isMerge = slug.includes("merge");
  const isReverseList = slug.includes("reverse") && slug.includes("list");
  const isTemperatures = slug.includes("temperatures");
  const isLevelOrder = slug.includes("level") || slug.includes("traverse");
  const isLca = slug.includes("lca") || slug.includes("ancestor");
  const isIslands = slug.includes("island");
  const isCloneGraph = slug.includes("clone");
  const isFrequent = slug.includes("frequent") || slug.includes("frequency");
  const isCoin = slug.includes("coin");
  const isIncreasing = slug.includes("increasing");

  // Format Names
  let words = slug.replace(/[^a-zA-Z0-9]/g, " ").trim().split(/\s+/);
  const camelName = words.map((w, i) => i === 0 ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join("");
  const snakeName = words.map(w => w.toLowerCase()).join("_");
  const pascalName = words.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join("");

  switch (targetLang) {
    case "python":
      if (isParentheses) return `def ${snakeName}(s: str) -> bool:\n    # Write your code here\n    pass\n`;
      if (isReverseString) return `def ${snakeName}(s: list[str]) -> None:\n    # Write your code here\n    # Do not return anything, modify s in-place.\n    pass\n`;
      if (isStock) return `def max_profit(prices: list[int]) -> int:\n    # Write your code here\n    pass\n`;
      if (isDuplicate) return `def contains_duplicate(nums: list[int]) -> bool:\n    # Write your code here\n    pass\n`;
      if (isProduct) return `def product_except_self(nums: list[int]) -> list[int]:\n    # Write your code here\n    pass\n`;
      if (isSubarray) return `def max_sub_array(nums: list[int]) -> int:\n    # Write your code here\n    pass\n`;
      if (is3Sum) return `def three_sum(nums: list[int]) -> list[list[int]]:\n    # Write your code here\n    pass\n`;
      if (isSubstring) return `def length_of_longest_substring(s: str) -> int:\n    # Write your code here\n    pass\n`;
      if (isBinarySearch || isRotated) return `def search(nums: list[int], target: int) -> int:\n    # Write your code here\n    pass\n`;
      if (isMerge) return `def merge_two_lists(list1, list2):\n    # Write your code here\n    pass\n`;
      if (isReverseList) return `def reverse_list(head):\n    # Write your code here\n    pass\n`;
      if (isTemperatures) return `def daily_temperatures(temperatures: list[int]) -> list[int]:\n    # Write your code here\n    pass\n`;
      if (isLevelOrder) return `def level_order(root):\n    # Write your code here\n    pass\n`;
      if (isLca) return `def lowest_common_ancestor(root, p, q):\n    # Write your code here\n    pass\n`;
      if (isIslands) return `def num_islands(grid: list[list[str]]) -> int:\n    # Write your code here\n    pass\n`;
      if (isCloneGraph) return `def clone_graph(node):\n    # Write your code here\n    pass\n`;
      if (isFrequent) return `def top_k_frequent(nums: list[int], k: int) -> list[int]:\n    # Write your code here\n    pass\n`;
      if (isCoin) return `def coin_change(coins: list[int], amount: int) -> int:\n    # Write your code here\n    pass\n`;
      if (isIncreasing) return `def length_of_lis(nums: list[int]) -> int:\n    # Write your code here\n    pass\n`;
      return `def ${snakeName}(nums: list[int], target: int) -> list[int]:\n    # Write your code here\n    pass\n`;

    case "javascript":
      if (isParentheses) return `function ${camelName}(s) {\n    // Write your code here\n    \n}\n`;
      if (isReverseString) return `function ${camelName}(s) {\n    // Write your code here\n    \n}\n`;
      if (isStock) return `function maxProfit(prices) {\n    // Write your code here\n    \n}\n`;
      if (isDuplicate) return `function containsDuplicate(nums) {\n    // Write your code here\n    \n}\n`;
      if (isProduct) return `function productExceptSelf(nums) {\n    // Write your code here\n    \n}\n`;
      if (isSubarray) return `function maxSubArray(nums) {\n    // Write your code here\n    \n}\n`;
      if (is3Sum) return `function threeSum(nums) {\n    // Write your code here\n    \n}\n`;
      if (isSubstring) return `function lengthOfLongestSubstring(s) {\n    // Write your code here\n    \n}\n`;
      if (isBinarySearch || isRotated) return `function search(nums, target) {\n    // Write your code here\n    \n}\n`;
      if (isMerge) return `function mergeTwoLists(list1, list2) {\n    // Write your code here\n    \n}\n`;
      if (isReverseList) return `function reverseList(head) {\n    // Write your code here\n    \n}\n`;
      if (isTemperatures) return `function dailyTemperatures(temperatures) {\n    // Write your code here\n    \n}\n`;
      if (isLevelOrder) return `function levelOrder(root) {\n    // Write your code here\n    \n}\n`;
      if (isLca) return `function lowestCommonAncestor(root, p, q) {\n    // Write your code here\n    \n}\n`;
      if (isIslands) return `function numIslands(grid) {\n    // Write your code here\n    \n}\n`;
      if (isCloneGraph) return `function cloneGraph(node) {\n    // Write your code here\n    \n}\n`;
      if (isFrequent) return `function topKFrequent(nums, k) {\n    // Write your code here\n    \n}\n`;
      if (isCoin) return `function coinChange(coins, amount) {\n    // Write your code here\n    \n}\n`;
      if (isIncreasing) return `function lengthOfLIS(nums) {\n    // Write your code here\n    \n}\n`;
      return `function ${camelName}(nums, target) {\n    // Write your code here\n    \n}\n`;

    case "typescript":
      if (isParentheses) return `function ${camelName}(s: string): boolean {\n    // Write your code here\n    return false;\n}\n`;
      if (isReverseString) return `function ${camelName}(s: string[]): void {\n    // Write your code here\n    \n}\n`;
      if (isStock) return `function maxProfit(prices: number[]): number {\n    // Write your code here\n    return 0;\n}\n`;
      if (isDuplicate) return `function containsDuplicate(nums: number[]): boolean {\n    // Write your code here\n    return false;\n}\n`;
      if (isProduct) return `function productExceptSelf(nums: number[]): number[] {\n    // Write your code here\n    return [];\n}\n`;
      if (isSubarray) return `function maxSubArray(nums: number[]): number {\n    // Write your code here\n    return 0;\n}\n`;
      if (is3Sum) return `function threeSum(nums: number[]): number[][] {\n    // Write your code here\n    return [];\n}\n`;
      if (isSubstring) return `function lengthOfLongestSubstring(s: string): number {\n    // Write your code here\n    return 0;\n}\n`;
      if (isBinarySearch || isRotated) return `function search(nums: number[], target: number): number {\n    // Write your code here\n    return 0;\n}\n`;
      if (isMerge) return `function mergeTwoLists(list1: any, list2: any): any {\n    // Write your code here\n    return null;\n}\n`;
      if (isReverseList) return `function reverseList(head: any): any {\n    // Write your code here\n    return null;\n}\n`;
      if (isTemperatures) return `function dailyTemperatures(temperatures: number[]): number[] {\n    // Write your code here\n    return [];\n}\n`;
      if (isLevelOrder) return `function levelOrder(root: any): number[][] {\n    // Write your code here\n    return [];\n}\n`;
      if (isLca) return `function lowestCommonAncestor(root: any, p: any, q: any): any {\n    // Write your code here\n    return null;\n}\n`;
      if (isIslands) return `function numIslands(grid: string[][]): number {\n    // Write your code here\n    return 0;\n}\n`;
      if (isCloneGraph) return `function cloneGraph(node: any): any {\n    // Write your code here\n    return null;\n}\n`;
      if (isFrequent) return `function topKFrequent(nums: number[], k: number): number[] {\n    // Write your code here\n    return [];\n}\n`;
      if (isCoin) return `function coinChange(coins: number[], amount: number): number {\n    // Write your code here\n    return 0;\n}\n`;
      if (isIncreasing) return `function lengthOfLIS(nums: number[]): number {\n    // Write your code here\n    return 0;\n}\n`;
      return `function ${camelName}(nums: number[], target: number): number[] {\n    // Write your code here\n    return [];\n}\n`;

    case "java":
      if (isParentheses) return `class Solution {\n    public boolean ${camelName}(String s) {\n        // Write your code here\n        return false;\n    }\n}\n`;
      if (isReverseString) return `class Solution {\n    public void ${camelName}(char[] s) {\n        // Write your code here\n    }\n}\n`;
      if (isStock) return `class Solution {\n    public int maxProfit(int[] prices) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isDuplicate) return `class Solution {\n    public boolean containsDuplicate(int[] nums) {\n        // Write your code here\n        return false;\n    }\n}\n`;
      if (isProduct) return `class Solution {\n    public int[] productExceptSelf(int[] nums) {\n        // Write your code here\n        return new int[]{};\n    }\n}\n`;
      if (isSubarray) return `class Solution {\n    public int maxSubArray(int[] nums) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (is3Sum) return `import java.util.*;\n\nclass Solution {\n    public List<List<Integer>> threeSum(int[] nums) {\n        // Write your code here\n        return new ArrayList<>();\n    }\n}\n`;
      if (isSubstring) return `class Solution {\n    public int lengthOfLongestSubstring(String s) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isBinarySearch || isRotated) return `class Solution {\n    public int search(int[] nums, int target) {\n        // Write your code here\n        return -1;\n    }\n}\n`;
      return `class Solution {\n    public int[] ${camelName}(int[] nums, int target) {\n        // Write your code here\n        return new int[]{};\n    }\n}\n`;

    case "cpp":
      if (isParentheses) return `#include <string>\nusing namespace std;\n\nclass Solution {\npublic:\n    bool ${camelName}(string s) {\n        // Write your code here\n        return false;\n    }\n};\n`;
      if (isReverseString) return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    void ${camelName}(vector<char>& s) {\n        // Write your code here\n    }\n};\n`;
      if (isStock) return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    int maxProfit(vector<int>& prices) {\n        // Write your code here\n        return 0;\n    }\n};\n`;
      if (isDuplicate) return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    bool containsDuplicate(vector<int>& nums) {\n        // Write your code here\n        return false;\n    }\n};\n`;
      if (isProduct) return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> productExceptSelf(vector<int>& nums) {\n        // Write your code here\n        return {};\n    }\n};\n`;
      if (isSubarray) return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    int maxSubArray(vector<int>& nums) {\n        // Write your code here\n        return 0;\n    }\n};\n`;
      if (is3Sum) return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<vector<int>> threeSum(vector<int>& nums) {\n        // Write your code here\n        return {};\n    }\n};\n`;
      if (isSubstring) return `#include <string>\nusing namespace std;\n\nclass Solution {\npublic:\n    int lengthOfLongestSubstring(string s) {\n        // Write your code here\n        return 0;\n    }\n};\n`;
      if (isBinarySearch || isRotated) return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    int search(vector<int>& nums, int target) {\n        // Write your code here\n        return -1;\n    }\n};\n`;
      return `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> ${camelName}(vector<int>& nums, int target) {\n        // Write your code here\n        return {};\n    }\n};\n`;

    case "csharp":
      if (isParentheses) return `public class Solution {\n    public bool ${pascalName}(string s) {\n        // Write your code here\n        return false;\n    }\n}\n`;
      if (isReverseString) return `public class Solution {\n    public void ${pascalName}(char[] s) {\n        // Write your code here\n    }\n}\n`;
      if (isStock) return `public class Solution {\n    public int MaxProfit(int[] prices) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isDuplicate) return `public class Solution {\n    public bool ContainsDuplicate(int[] nums) {\n        // Write your code here\n        return false;\n    }\n}\n`;
      if (isProduct) return `public class Solution {\n    public int[] ProductExceptSelf(int[] nums) {\n        // Write your code here\n        return new int[]{};\n    }\n}\n`;
      if (isSubarray) return `public class Solution {\n    public int MaxSubArray(int[] nums) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (is3Sum) return `using System.Collections.Generic;\n\npublic class Solution {\n    public IList<IList<int>> ThreeSum(int[] nums) {\n        // Write your code here\n        return new List<IList<int>>();\n    }\n}\n`;
      if (isSubstring) return `public class Solution {\n    public int LengthOfLongestSubstring(string s) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isBinarySearch || isRotated) return `public class Solution {\n    public int Search(int[] nums, int target) {\n        // Write your code here\n        return -1;\n    }\n}\n`;
      return `public class Solution {\n    public int[] ${pascalName}(int[] nums, int target) {\n        // Write your code here\n        return new int[]{};\n    }\n}\n`;

    case "rust":
      if (isParentheses) return `impl Solution {\n    pub fn is_valid(s: String) -> bool {\n        // Write your code here\n        false\n    }\n}\n`;
      if (isReverseString) return `impl Solution {\n    pub fn reverse_string(s: &mut Vec<char>) {\n        // Write your code here\n    }\n}\n`;
      if (isStock) return `impl Solution {\n    pub fn max_profit(prices: Vec<i32>) -> i32 {\n        // Write your code here\n        0\n    }\n}\n`;
      if (isDuplicate) return `impl Solution {\n    pub fn contains_duplicate(nums: Vec<i32>) -> bool {\n        // Write your code here\n        false\n    }\n}\n`;
      if (isProduct) return `impl Solution {\n    pub fn product_except_self(nums: Vec<i32>) -> Vec<i32> {\n        // Write your code here\n        vec![]\n    }\n}\n`;
      if (isSubarray) return `impl Solution {\n    pub fn max_sub_array(nums: Vec<i32>) -> i32 {\n        // Write your code here\n        0\n    }\n}\n`;
      if (is3Sum) return `impl Solution {\n    pub fn three_sum(nums: Vec<i32>) -> Vec<Vec<i32>> {\n        // Write your code here\n        vec![]\n    }\n}\n`;
      if (isSubstring) return `impl Solution {\n    pub fn length_of_longest_substring(s: String) -> i32 {\n        // Write your code here\n        0\n    }\n}\n`;
      if (isBinarySearch || isRotated) return `impl Solution {\n    pub fn search(nums: Vec<i32>, target: i32) -> i32 {\n        // Write your code here\n        -1\n    }\n}\n`;
      return `impl Solution {\n    pub fn ${snakeName}(nums: Vec<i32>, target: i32) -> Vec<i32> {\n        // Write your code here\n        vec![]\n    }\n}\n`;

    case "go":
      if (isParentheses) return `func isValid(s string) bool {\n    // Write your code here\n    return false\n}\n`;
      if (isReverseString) return `func reverseString(s []byte)  {\n    // Write your code here\n}\n`;
      if (isStock) return `func maxProfit(prices []int) int {\n    // Write your code here\n    return 0\n}\n`;
      if (isDuplicate) return `func containsDuplicate(nums []int) bool {\n    // Write your code here\n    return false\n}\n`;
      if (isProduct) return `func productExceptSelf(nums []int) []int {\n    // Write your code here\n    return []int{}\n}\n`;
      if (isSubarray) return `func maxSubArray(nums []int) int {\n    // Write your code here\n    return 0\n}\n`;
      if (is3Sum) return `func threeSum(nums []int) [][]int {\n    // Write your code here\n    return [][]int{}\n}\n`;
      if (isSubstring) return `func lengthOfLongestSubstring(s string) int {\n    // Write your code here\n    return 0\n}\n`;
      if (isBinarySearch || isRotated) return `func search(nums []int, target int) int {\n    // Write your code here\n    return -1\n}\n`;
      return `func ${camelName}(nums []int, target int) []int {\n    // Write your code here\n    return []int{}\n}\n`;

    case "php":
      if (isParentheses) return `class Solution {\n    function isValid($s) {\n        // Write your code here\n        return false;\n    }\n}\n`;
      if (isReverseString) return `class Solution {\n    function reverseString(&$s) {\n        // Write your code here\n    }\n}\n`;
      if (isStock) return `class Solution {\n    function maxProfit($prices) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isDuplicate) return `class Solution {\n    function containsDuplicate($nums) {\n        // Write your code here\n        return false;\n    }\n}\n`;
      if (isProduct) return `class Solution {\n    function productExceptSelf($nums) {\n        // Write your code here\n        return [];\n    }\n}\n`;
      if (isSubarray) return `class Solution {\n    function maxSubArray($nums) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (is3Sum) return `class Solution {\n    function threeSum($nums) {\n        // Write your code here\n        return [];\n    }\n}\n`;
      if (isSubstring) return `class Solution {\n    function lengthOfLongestSubstring($s) {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isBinarySearch || isRotated) return `class Solution {\n    function search($nums, $target) {\n        // Write your code here\n        return -1;\n    }\n}\n`;
      return `class Solution {\n    function ${camelName}($nums, $target) {\n        // Write your code here\n        return [];\n    }\n}\n`;

    case "ruby":
      if (isParentheses) return `def is_valid(s)\n    # Write your code here\nend\n`;
      if (isReverseString) return `def reverse_string(s)\n    # Write your code here\nend\n`;
      if (isStock) return `def max_profit(prices)\n    # Write your code here\nend\n`;
      if (isDuplicate) return `def contains_duplicate(nums)\n    # Write your code here\nend\n`;
      if (isProduct) return `def product_except_self(nums)\n    # Write your code here\nend\n`;
      if (isSubarray) return `def max_sub_array(nums)\n    # Write your code here\nend\n`;
      if (is3Sum) return `def three_sum(nums)\n    # Write your code here\nend\n`;
      if (isSubstring) return `def length_of_longest_substring(s)\n    # Write your code here\nend\n`;
      if (isBinarySearch || isRotated) return `def search(nums, target)\n    # Write your code here\nend\n`;
      return `def ${snakeName}(nums, target)\n    # Write your code here\nend\n`;

    case "swift":
      if (isParentheses) return `class Solution {\n    func isValid(_ s: String) -> Bool {\n        // Write your code here\n        return false\n    }\n}\n`;
      if (isReverseString) return `class Solution {\n    func reverseString(_ s: inout [Character]) {\n        // Write your code here\n    }\n}\n`;
      if (isStock) return `class Solution {\n    func maxProfit(_ prices: [Int]) -> Int {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isDuplicate) return `class Solution {\n    func containsDuplicate(_ nums: [Int]) -> Bool {\n        // Write your code here\n        return false;\n    }\n}\n`;
      if (isProduct) return `class Solution {\n    func productExceptSelf(_ nums: [Int]) -> [Int] {\n        // Write your code here\n        return [];\n    }\n}\n`;
      if (isSubarray) return `class Solution {\n    func maxSubArray(_ nums: [Int]) -> Int {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (is3Sum) return `class Solution {\n    func threeSum(_ nums: [Int]) -> [[Int]] {\n        // Write your code here\n        return [];\n    }\n}\n`;
      if (isSubstring) return `class Solution {\n    func lengthOfLongestSubstring(_ s: String) -> Int {\n        // Write your code here\n        return 0;\n    }\n}\n`;
      if (isBinarySearch || isRotated) return `class Solution {\n    func search(_ nums: [Int], _ target: Int) -> Int {\n        // Write your code here\n        return -1;\n    }\n}\n`;
      return `class Solution {\n    func ${camelName}(_ nums: [Int], _ target: Int) -> [Int] {\n        // Write your code here\n        return [];\n    }\n}\n`;

    case "kotlin":
      if (isParentheses) return `class Solution {\n    fun isValid(s: String): Boolean {\n        // Write your code here\n        return false\n    }\n}\n`;
      if (isReverseString) return `class Solution {\n    fun reverseString(s: CharArray): Unit {\n        // Write your code here\n    }\n}\n`;
      if (isStock) return `class Solution {\n    fun maxProfit(prices: IntArray): Int {\n        // Write your code here\n        return 0\n    }\n}\n`;
      if (isDuplicate) return `class Solution {\n    fun containsDuplicate(nums: IntArray): Boolean {\n        // Write your code here\n        return false\n    }\n}\n`;
      if (isProduct) return `class Solution {\n    fun productExceptSelf(nums: IntArray): IntArray {\n        // Write your code here\n        return intArrayOf()\n    }\n}\n`;
      if (isSubarray) return `class Solution {\n    fun maxSubArray(nums: IntArray): Int {\n        // Write your code here\n        return 0\n    }\n}\n`;
      if (is3Sum) return `class Solution {\n    fun threeSum(nums: IntArray): List<List<Int>> {\n        // Write your code here\n        return listOf()\n    }\n}\n`;
      if (isSubstring) return `class Solution {\n    fun lengthOfLongestSubstring(s: String): Int {\n        // Write your code here\n        return 0\n    }\n}\n`;
      if (isBinarySearch || isRotated) return `class Solution {\n    fun search(nums: IntArray, target: Int): Int {\n        // Write your code here\n        return -1;\n    }\n}\n`;
      return `class Solution {\n    fun ${camelName}(nums: IntArray, target: Int): IntArray {\n        // Write your code here\n        return intArrayOf()\n    }\n}\n`;

    case "sql":
      return `-- Write your SQL query here\nSELECT * FROM table_name;\n`;

    default:
      return defaultCodeTemplates[targetLang] || "";
  }
};

const renderMarkdown = (text) => {
  if (!text) return null;
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    
    // Filter out common raw JSON brackets or prompt leaks
    if (trimmed === "{" || trimmed === "}" || trimmed === "}," || trimmed === "[{" || trimmed === "}]" || trimmed === '"' || trimmed === "'") {
      return null;
    }
    const lowerLine = trimmed.toLowerCase();
    if (
      lowerLine.startsWith("return only") || 
      lowerLine.startsWith("expected json") || 
      lowerLine.startsWith("return a json") ||
      lowerLine.includes("preamble") ||
      lowerLine.includes("markdown codeblock") ||
      (lowerLine.includes("time_complexity") && lowerLine.includes("string")) ||
      (lowerLine.includes("space_complexity") && lowerLine.includes("string")) ||
      (lowerLine.includes("ai_review") && lowerLine.includes("string"))
    ) {
      return null;
    }

    // Clean up em-dashes and en-dashes from headers and content
    let cleanLine = line
      .replace(/—/g, "-")
      .replace(/–/g, "-");

    // Headers
    if (cleanLine.startsWith("## ")) {
      const headerText = cleanLine.replace("## ", "").replace(/^[-—–\s]+/, "").trim();
      return <h2 key={idx} style={{ fontSize: "15px", fontWeight: 800, marginTop: "12px", marginBottom: "6px", color: "var(--cyan)" }}>{headerText}</h2>;
    }
    if (cleanLine.startsWith("### ")) {
      const headerText = cleanLine.replace("### ", "").replace(/^[-—–\s]+/, "").trim();
      return <h3 key={idx} style={{ fontSize: "13px", fontWeight: 700, marginTop: "10px", marginBottom: "4px", color: "#fff" }}>{headerText}</h3>;
    }
    if (cleanLine.startsWith("#### ")) {
      const headerText = cleanLine.replace("#### ", "").replace(/^[-—–\s]+/, "").trim();
      return <h4 key={idx} style={{ fontSize: "12px", fontWeight: 700, marginTop: "8px", marginBottom: "4px", color: "var(--purple)" }}>{headerText}</h4>;
    }
    
    // Check if bullet point (supporting *, -, and dashes)
    let content = cleanLine;
    let isBullet = false;
    const cleanTrimmed = cleanLine.trim();
    if (cleanTrimmed.startsWith("* ") || cleanTrimmed.startsWith("- ")) {
      isBullet = true;
      content = cleanTrimmed.substring(2);
    }
    
    // Parse bold text like **something**
    const parts = [];
    let lastIndex = 0;
    const regex = /\*\*(.*?)\*\*/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      parts.push(<strong key={match.index} style={{ color: "var(--cyan)", fontWeight: 700 }}>{match[1]}</strong>);
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }
    
    const displayContent = parts.length > 0 ? parts : content;
    
    if (isBullet) {
      return (
        <div key={idx} style={{ display: "flex", gap: "6px", paddingLeft: "12px", marginBottom: "4px" }}>
          <span style={{ color: "var(--cyan)" }}>•</span>
          <div>{displayContent}</div>
        </div>
      );
    }
    
    return (
      <div key={idx} style={{ marginBottom: "6px" }}>
        {displayContent}
      </div>
    );
  });
};

export default function CodingTab({ apiFetch, isLoggedIn, user = {} }) {
  const [lang, setLang] = useState("python");
  const [code, setCode] = useState(defaultCodeTemplates.python);
  const [consoleOut, setConsoleOut] = useState("Ready to run...");
  const [consoleColor, setConsoleColor] = useState("var(--text2)");
  const [timeComplexity, setTimeComplexity] = useState("—");
  const [spaceComplexity, setSpaceComplexity] = useState("—");
  const [testPass, setTestPass] = useState("—");
  const [testPassColor, setTestPassColor] = useState("var(--text2)");
  const [aiReview, setAiReview] = useState("Run your code to get AI feedback on time complexity, space complexity, and edge cases.");
  const [hintBox, setHintBox] = useState("Click below to get a hint from your AI coach.");
  const [hintIdx, setHintIdx] = useState(0);
  const [testCaseResults, setTestCaseResults] = useState(null);

  // --- Coding Room and Sheet Upload States ---
  const [problems, setProblems] = useState([]);
  const [currentProblem, setCurrentProblem] = useState(null);
  
  const [roomId, setRoomId] = useState("");
  const [roomParticipants, setRoomParticipants] = useState([]);
  const [joinRoomInput, setJoinRoomInput] = useState("");
  
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [selectedSheetId, setSelectedSheetId] = useState("");
  const [sheetsList, setSheetsList] = useState([]); // tracks parsed sheets

  // Refs for typing state synchronization and stable polling
  const lastTypedRef = useRef(Date.now());
  const isEditingRef = useRef(false);
  const codeRef = useRef(code);
  const langRef = useRef(lang);
  const consoleOutRef = useRef(consoleOut);
  const editDebounceRef = useRef(null);
  const syncIntervalRef = useRef(null);

  // Keep refs in sync with state
  useEffect(() => { codeRef.current = code; }, [code]);
  useEffect(() => { langRef.current = lang; }, [lang]);
  useEffect(() => { consoleOutRef.current = consoleOut; }, [consoleOut]);


  // ── Reload & URL persistence: restore room from URL param or sessionStorage ──
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const urlRoomId = urlParams.get("room");
    const savedRoomId = urlRoomId || sessionStorage.getItem("coding_room_id");
    if (savedRoomId) {
      const savedUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user";
      const savedUserName = user?.name || localStorage.getItem("user_name") || localStorage.getItem("user_email")?.split('@')[0] || "User";
      apiFetch('/api/coding/room/join', {
        method: 'POST',
        body: JSON.stringify({
          room_id: savedRoomId.toUpperCase(),
          user_id: savedUserId,
          user_name: savedUserName,
          role: user?.role || "candidate"
        })
      }).then(res => res.ok ? res.json() : null).then(data => {
        if (data) {
          setRoomId(data.room_id);
          sessionStorage.setItem("coding_room_id", data.room_id);
          if (!urlParams.get("room")) {
            window.history.replaceState(null, "", `?room=${data.room_id}`);
          }
          if (data.problem) setCurrentProblem(data.problem);
          if (data.current_code) { setCode(data.current_code); codeRef.current = data.current_code; }
          if (data.current_lang) { setLang(data.current_lang); langRef.current = data.current_lang; }
          if (data.participants) {
            const parsed = Array.isArray(data.participants) ? data.participants : (typeof data.participants === 'string' ? JSON.parse(data.participants) : []);
            setRoomParticipants(parsed);
          }
          if (data.current_output) {
            setConsoleOut(data.current_output);
            setConsoleColor("var(--text2)");
          }
        }
      }).catch(() => {
        sessionStorage.removeItem("coding_room_id");
        window.history.replaceState(null, "", window.location.pathname);
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 1. Fetch available problems on mount
  useEffect(() => {
    fetchProblems();
  }, []);

  const fetchProblems = async (sheetId = "") => {
    try {
      const url = sheetId ? `/api/coding/problems?sheet_id=${sheetId}` : '/api/coding/problems';
      const res = await apiFetch(url);
      if (res.ok) {
        const data = await res.json();
        const problemsList = Array.isArray(data) ? data : (data.problems || []);
        setProblems(problemsList);
        
        const pendingPid = localStorage.getItem("selected_problem_id");
        if (pendingPid) {
          const found = problemsList.find(p => (p.problem_id === pendingPid || p.id === pendingPid));
          if (found) {
            selectProblem(found);
            localStorage.removeItem("selected_problem_id");
            return;
          }
        }

        if (problemsList.length > 0) {
          const defaultProb = problemsList.find(p => (p.problem_id === "prob_01" || p.problem_id === "two-sum" || p.id === "prob_01")) || problemsList[0];
          selectProblem(defaultProb);
        }
      }
    } catch (e) {
      console.error("Error fetching problems:", e);
    }
  };

  // 2. Stable Synchronization Polling loop (depends ONLY on roomId)
  useEffect(() => {
    if (roomId) {
      syncRoomState(false); // immediate poll on room entry
      syncIntervalRef.current = setInterval(() => syncRoomState(false), 800);
    } else {
      if (syncIntervalRef.current) clearInterval(syncIntervalRef.current);
    }
    return () => {
      if (syncIntervalRef.current) clearInterval(syncIntervalRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId]);

  const syncRoomState = async (isExplicitEdit = false) => {
    if (!roomId) return;
    try {
      const myUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "anonymous_user";
      const myUserName = user?.name || localStorage.getItem("user_name") || localStorage.getItem("user_email")?.split('@')[0] || "User";
      const shouldSendEdit = isExplicitEdit || isEditingRef.current;
      
      if (shouldSendEdit) {
        isEditingRef.current = false;
      }

      const payload = {
        room_id: roomId,
        user_id: myUserId,
        user_name: myUserName,
        cursor: getCursorPosition(),
        code: codeRef.current,
        lang: langRef.current,
        is_editing: shouldSendEdit
      };

      const res = await apiFetch('/api/coding/room/sync', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        const data = await res.json();
        const parsedP = Array.isArray(data.participants) ? data.participants : (typeof data.participants === 'string' ? JSON.parse(data.participants) : []);
        setRoomParticipants(parsedP);
        
        const timeSinceType = Date.now() - lastTypedRef.current;
        // Update local editor if server code comes from another participant or differs
        if (data.current_code !== undefined && data.last_editor !== myUserId && timeSinceType > 300) {
          if (data.current_code !== codeRef.current) {
            setCode(data.current_code);
            codeRef.current = data.current_code;
          }
        }
        if (data.current_lang && data.current_lang !== langRef.current) {
          setLang(data.current_lang);
          langRef.current = data.current_lang;
        }
        if (data.current_output && data.current_output !== consoleOutRef.current) {
          setConsoleOut(data.current_output);
          consoleOutRef.current = data.current_output;
          setConsoleColor("var(--text2)");
        }
      }
    } catch (err) {
      console.error("Room synchronization error:", err);
    }
  };

  // Push code edit to room with debounce
  const handleCodeChange = (newCode) => {
    setCode(newCode);
    codeRef.current = newCode;
    lastTypedRef.current = Date.now();
    isEditingRef.current = true;

    if (roomId) {
      if (editDebounceRef.current) clearTimeout(editDebounceRef.current);
      editDebounceRef.current = setTimeout(() => {
        syncRoomState(true);
      }, 200);
    }
  };

  // Push run output to room so all participants see it
  const pushOutputToRoom = async (outputText) => {
    setConsoleOut(outputText);
    consoleOutRef.current = outputText;
    if (!roomId) return;
    try {
      const myUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "user";
      const myUserName = user?.name || localStorage.getItem("user_name") || "User";
      await apiFetch('/api/coding/room/sync', {
        method: 'POST',
        body: JSON.stringify({
          room_id: roomId,
          user_id: myUserId,
          user_name: myUserName,
          output: outputText,
        })
      });
    } catch (_) {}
  };


  const getCursorPosition = () => {
    const area = document.getElementById("code-textarea");
    if (!area) return { line: 1, col: 1, ch: 0 };
    const start = area.selectionStart;
    const textBefore = area.value.substring(0, start);
    const lineList = textBefore.split("\n");
    const currentLine = lineList.length;
    const lastLineText = lineList[lineList.length - 1];
    return { 
      line: currentLine, 
      col: lastLineText.length + 1, 
      ch: lastLineText.length,
      selectionStart: area.selectionStart,
      selectionEnd: area.selectionEnd
    };
  };

  // 3. Selection of problem helper
  const selectProblem = (problem) => {
    setCurrentProblem(problem);
    setHintIdx(0);
    setHintBox("Click below to get a hint from your AI coach.");
    
    const template = getDynamicStarterCode(problem, lang);
    setCode(template);
    codeRef.current = template;
  };

  const handleProblemChange = (e) => {
    const pid = e.target.value;
    const found = problems.find(p => p.problem_id === pid);
    if (found) {
      if (roomId) {
        assignProblemToRoom(pid);
      } else {
        selectProblem(found);
      }
    }
  };

  const assignProblemToRoom = async (pid) => {
    try {
      const res = await apiFetch('/api/coding/room/assign-question', {
        method: 'POST',
        body: JSON.stringify({ room_id: roomId, problem_id: pid })
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentProblem(data.problem);
        setCode(data.current_code);
        codeRef.current = data.current_code;
        setLang(data.current_lang);
        langRef.current = data.current_lang;
      }
    } catch (err) {
      console.error("Failed to assign problem to room:", err);
    }
  };

  // 4. Room operations
  const createRoom = async () => {
    try {
      const myUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "interviewer_user";
      const myUserName = user?.name || localStorage.getItem("user_name") || localStorage.getItem("user_email")?.split('@')[0] || "Interviewer";
      const res = await apiFetch('/api/coding/room/create', {
        method: 'POST',
        body: JSON.stringify({
          user_id: myUserId,
          user_name: myUserName,
          problem_id: currentProblem?.problem_id,
          sheet_id: selectedSheetId
        })
      });
      if (res.ok) {
        const data = await res.json();
        setRoomId(data.room_id);
        sessionStorage.setItem("coding_room_id", data.room_id);
        window.history.replaceState(null, "", `?room=${data.room_id}`);
        setCurrentProblem(data.problem);
        setCode(data.current_code);
        codeRef.current = data.current_code;
        setLang(data.current_lang);
        langRef.current = data.current_lang;
        setRoomParticipants(data.participants);
        setConsoleOut(`Joined Room ${data.room_id}. Editor synchronized!`);
      }
    } catch (err) {
      console.error("Create room error:", err);
    }
  };

  const joinRoom = async () => {
    const rId = joinRoomInput.trim().toUpperCase();
    if (!rId) return;
    try {
      const myUserName = user?.name || localStorage.getItem("user_name") || localStorage.getItem("user_email")?.split('@')[0] || "Candidate";
      const myUserId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "candidate_user";
      const res = await apiFetch('/api/coding/room/join', {
        method: 'POST',
        body: JSON.stringify({
          room_id: rId,
          user_id: myUserId,
          user_name: myUserName,
          role: user?.role || "candidate"
        })
      });
      if (res.ok) {
        const data = await res.json();
        setRoomId(data.room_id);
        sessionStorage.setItem("coding_room_id", data.room_id);
        window.history.replaceState(null, "", `?room=${data.room_id}`);
        setCurrentProblem(data.problem);
        setCode(data.current_code);
        codeRef.current = data.current_code;
        setLang(data.current_lang);
        langRef.current = data.current_lang;
        setRoomParticipants(data.participants);
        if (data.current_output) {
          setConsoleOut(data.current_output);
        } else {
          setConsoleOut(`Successfully joined Room ${data.room_id}!`);
        }
      } else {
        const err = await res.json();
        alert(err.error || "Room not found");
      }
    } catch (err) {
      console.error("Join room error:", err);
    }
  };

  const leaveRoom = () => {
    setRoomId("");
    setRoomParticipants([]);
    setJoinRoomInput("");
    sessionStorage.removeItem("coding_room_id");
    window.history.replaceState(null, "", window.location.pathname);
    if (problems.length > 0) {
      selectProblem(problems[0]);
    }
    setConsoleOut("Left room. Local playground activated.");
  };


  // 5. Document Upload
  const handleSheetUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsUploading(true);
    setUploadError("");
    
    const formData = new FormData();
    formData.append("sheet", file);
    formData.append("file", file);
    formData.append("user_id", user?._id || user?.user_id || user?.id || localStorage.getItem("user_id") || "recruiter");
    
    try {
      const res = await apiFetch('/api/coding/upload-sheet', {
        method: "POST",
        body: formData
      });
      
      const data = await res.json();
      if (res.ok) {
        // Save sheet info to checklist
        setSheetsList(prev => [...prev, { id: data.sheet_id, name: data.filename }]);
        setSelectedSheetId(data.sheet_id);
        
        // Refresh problems list with parsed questions
        await fetchProblems(data.sheet_id);
        if (data.problems && data.problems.length > 0) {
          selectProblem(data.problems[0]);
        }
        
        alert(`Questions parsed successfully! Extracted ${data.problems.length} problems.`);
      } else {
        setUploadError(data.error || "Failed to parse document");
      }
    } catch (err) {
      setUploadError("Network error uploading sheet.");
    } finally {
      setIsUploading(false);
      e.target.value = ""; // reset file input
    }
  };

  // 6. Running Code & AI Hints
  const handleLangChange = (newLang) => {
    setLang(newLang);
    langRef.current = newLang;
    const template = currentProblem ? getDynamicStarterCode(currentProblem, newLang) : (defaultCodeTemplates[newLang] || "");
    setCode(template);
    codeRef.current = template;
    if (roomId) {
      syncRoomState(true);
    }
  };

  const resetStarterCode = () => {
    if (!currentProblem) {
      setCode(defaultCodeTemplates[lang] || "");
      return;
    }
    const template = getDynamicStarterCode(currentProblem, lang);
    setCode(template);
  };

  const getHint = async () => {
    setHintBox("Getting hint...");
    try {
      const res = await apiFetch('/api/coding/hint', {
        method: 'POST',
        body: JSON.stringify({
          problem_id: currentProblem?.problem_id || 'two-sum',
          code: code,
          hint_index: hintIdx
        })
      });
      const data = await res.json();
      if (res.ok && data.hint) {
        setHintBox('💡 ' + data.hint);
        setHintIdx(prev => prev + 1);
        return;
      }
    } catch (e) {
      console.warn("Hint fetch notice:", e);
    }
    
    const pid = (currentProblem?.problem_id || '').toLowerCase();
    let localHint = "💡 Analyze the problem constraints to determine if a linear O(N) or logarithmic O(log N) algorithm is expected.";
    if (pid.includes("two-sum")) {
      localHint = hintIdx === 0 
        ? "💡 Try using a hash map to store each number's value and its index as you iterate." 
        : "💡 For each number x, check if (target - x) is already in your hash map.";
    } else if (pid.includes("parentheses")) {
      localHint = hintIdx === 0 
        ? "💡 A stack data structure is ideal for tracking open brackets in correct order." 
        : "💡 Push open brackets onto stack. For closing brackets, check if they match top of stack.";
    } else if (currentProblem?.title) {
      localHint = `💡 For '${currentProblem.title}', trace a small example input by hand to identify pattern boundaries.`;
    }
    setHintBox(localHint);
    setHintIdx(prev => prev + 1);
  };

  const runCode = async () => {
    setConsoleOut("⏳ Compiling and running tests in secure sandbox environment...");
    setConsoleColor("var(--text2)");
    setTimeComplexity("—");
    setSpaceComplexity("—");
    setTestPass("—");
    setTestCaseResults(null);
    setTestPassColor("var(--text2)");
    setAiReview("Analyzing logic...");

    // ── FIX Bug 3: Push "running" state to room immediately ──
    if (roomId) pushOutputToRoom("⏳ Partner running code...");

    try {
      const res = await apiFetch('/api/coding/submit', {
        method: 'POST',
        body: JSON.stringify({
          language: lang,
          code: code,
          problem_id: currentProblem?.problem_id || 'two-sum',
          user_id: user?._id || user?.user_id || user?.id || localStorage.getItem("user_id")
        })
      });
      const d = await res.json();
      if (res.ok) {
        setTestCaseResults(d.results || []);
        let outputText;
        if (d.stderr) {
          setConsoleColor('var(--red)');
          outputText = `Error:\n${d.stderr}`;
          setConsoleOut(outputText);
          setTestPass(`0/${d.total || 3}`);
          setTestPassColor('var(--red)');
          setAiReview(d.ai_review || "Code runner execution failed due to runtime exception.");
        } else {
          setConsoleColor(d.passed === d.total ? '#00d68f' : 'var(--orange)');
          outputText = d.stdout || 'Execution complete.';
          setConsoleOut(outputText);
          setTimeComplexity(d.time_complexity || '—');
          setSpaceComplexity(d.space_complexity || '—');
          setTestPass(`${d.passed}/${d.total}`);
          setTestPassColor(d.passed === d.total ? 'var(--cyan)' : 'var(--orange)');
          setAiReview(d.ai_review || 'No AI feedback generated.');
        }
        // ── FIX Bug 3: Broadcast final output to all room participants ──
        if (roomId) pushOutputToRoom(outputText);
      } else {
        setTestCaseResults([]);
        setConsoleColor('var(--red)');
        const errText = 'Error: ' + (d.error || 'Execution sandbox error');
        setConsoleOut(errText);
        if (roomId) pushOutputToRoom(errText);
      }
    } catch(e) {
      setTestCaseResults([]);
      setConsoleColor('var(--red)');
      setConsoleOut('Execution error: Network connection timeout.');
    }
  };


  return (
    <div id="page-coding" className="page active" role="tabpanel">
      <div className="container">
        
        {/* Header */}
        <div className="sec-header mb16">
          <div className="flex items-center gap8">
            <h1 className="sec-title" style={{fontSize:"18px"}}>Coding Room</h1>
            <span className="pill pill-cyan">{roomId ? `Room ${roomId}` : "Local Playground"}</span>
            {roomId && <span className="pill pill-purple">Sync Polling Active</span>}
          </div>
        </div>

        {/* Dynamic Collaboration and Room Management Panel */}
        <div className="collab-bar mb16" style={{
          display: "flex", 
          flexWrap: "wrap", 
          gap: "12px", 
          padding: "14px 18px", 
          background: "var(--bg3)", 
          border: "1px solid var(--border)", 
          borderRadius: "14px"
        }}>
          {!roomId ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", width: "100%", alignItems: "center" }}>
              <div style={{ marginRight: "10px" }}>
                <div style={{fontSize:"10px", fontWeight:800, color:"var(--text2)", textTransform:"uppercase", marginBottom:"2px"}}>COLLABORATION</div>
                <div className="text-sm font-semibold">Join or create a live room to code together</div>
              </div>
              <button className="btn btn-primary btn-sm" onClick={createRoom}>➕ Create Room</button>
              <div style={{ display: "flex", gap: "4px" }}>
                <input 
                  type="text" 
                  className="lang-select" 
                  style={{ width: "110px", height: "32px", fontSize: "12px", padding: "0 8px", background: "rgba(255,255,255,0.03)" }}
                  placeholder="ROOM ID" 
                  value={joinRoomInput}
                  onChange={(e) => setJoinRoomInput(e.target.value)}
                />
                <button className="btn btn-ghost btn-sm" onClick={joinRoom}>Join</button>
              </div>
              
              {/* Question Sheet Uploader */}
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "8px" }}>
                <label htmlFor="coding-sheet-upload" className="btn btn-cyan btn-sm" style={{ cursor: "pointer", margin: 0, display: "inline-flex", alignItems: "center", gap: "6px" }}>
                  📂 Upload Sheet
                </label>
                <input 
                  id="coding-sheet-upload"
                  type="file" 
                  style={{ display: "none" }} 
                  accept=".pdf,.doc,.docx,.xlsx,.csv,.txt,.md,.json" 
                  onChange={handleSheetUpload} 
                />
                {isUploading && <span style={{ fontSize: "11px", color: "var(--cyan)" }}>Parsing...</span>}
                {uploadError && <span style={{ fontSize: "11px", color: "var(--red)" }} title={uploadError}>⚠️ Error</span>}
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", width: "100%", alignItems: "center" }}>
              <div>
                <div style={{fontSize:"10px", fontWeight:800, color:"var(--cyan)", textTransform:"uppercase", marginBottom:"2px"}}>ACTIVE ROOM</div>
                <div style={{fontSize: "14px", fontWeight: 800, color: "#fff", display: "flex", alignItems: "center", gap: "6px"}}>
                  {roomId} 
                  <button className="btn-xs btn-ghost" style={{padding: "2px 6px"}} onClick={() => {
                    navigator.clipboard.writeText(roomId);
                    alert("Room ID copied to clipboard!");
                  }}>📋 Copy</button>
                </div>
              </div>
              
              {/* Connected participants list */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "10px" }}>
                <div style={{display:"flex", gap:"-4px", marginRight: "6px"}}>
                  {(Array.isArray(roomParticipants) ? roomParticipants : []).map((p, idx) => {
                    const myId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id");
                    const isSelf = p?.user_id === myId;
                    return (
                      <div 
                        key={p?.user_id || idx} 
                        className="c-av" 
                        style={{
                          background: p?.role === "interviewer" ? "#7c3aed" : "#0e7a5e",
                          border: isSelf ? "2px solid #f59e0b" : p?.active ? "2px solid var(--cyan)" : "2px solid transparent",
                          color: "#fff",
                          marginLeft: idx > 0 ? "-6px" : 0
                        }}
                        title={`${p?.name || 'User'}${isSelf ? ' (You)' : ''} · ${p?.role || 'participant'} · ${p?.active ? 'Active' : 'Idle'}`}
                      >
                        {(p?.name || "?").split(' ').map(n=>n[0]).join('').toUpperCase().slice(0,2)}
                      </div>
                    );
                  })}
                </div>
                <span className="text-xs text-muted" style={{maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"}}>
                  {(() => {
                    const myId = user?._id || user?.user_id || user?.id || localStorage.getItem("user_id");
                    const safeList = Array.isArray(roomParticipants) ? roomParticipants : [];
                    const others = safeList.filter(p => p && p.user_id !== myId && p.active);
                    if (others.length === 0) return "You're the only one here";
                    return `${others.map(p => p.name).join(", ")} also editing`;
                  })()}
                </span>
              </div>


              {/* Leave Room */}
              <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto", borderColor: "rgba(255,84,114,0.3)", color: "var(--red)" }} onClick={leaveRoom}>🚪 Leave Room</button>
            </div>
          )}
        </div>

        {/* Main Coding Layout */}
        <div className="code-layout">
          
          {/* Left panel: Problem description */}
          <div className="prob-panel">
            <div className="flex items-center gap8 mb8" style={{justifyContent: "space-between"}}>
              <div className="flex gap8">
                <span className={`pill ${currentProblem?.difficulty === 'Hard' ? 'pill-red' : currentProblem?.difficulty === 'Medium' ? 'pill-gold' : 'pill-cyan'}`}>
                  {currentProblem?.difficulty || "Easy"}
                </span>
                <span className="tag">{currentProblem?.category || "Algorithm"}</span>
              </div>
              
              {/* Problem selector dropdown */}
              <select 
                className="lang-select prob-select" 
                style={{
                  height: "24px", 
                  padding: "0 6px", 
                  fontSize: "10.5px", 
                  maxWidth: "135px", 
                  overflow: "hidden", 
                  textOverflow: "ellipsis", 
                  whiteSpace: "nowrap",
                  backgroundColor: "#0c1220",
                  color: "#f0f4fd",
                  borderRadius: "6px"
                }}
                value={currentProblem?.problem_id || ""} 
                onChange={handleProblemChange}
              >
                <option value="" disabled style={{ background: "#0c1220", color: "#8a9bc0" }}>Select Problem...</option>
                {problems.map(p => (
                  <option key={p.problem_id} value={p.problem_id} style={{ background: "#0c1220", color: "#f0f4fd" }}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div style={{fontSize:"17px", fontWeight:800, marginBottom:"3px"}}>{currentProblem?.title || "Loading Problem..."}</div>
              {currentProblem?.sheet_id && <div style={{fontSize:"10px", color:"var(--purple)", fontWeight:700}}>CUSTOM SHEET ASSIGNED</div>}
            </div>

            <div className="text-sm" style={{color:"#b0c0d8", lineHeight:1.7, marginTop: "10px", overflowY: "auto", maxHeight: "220px"}}>
              {currentProblem?.description}
            </div>

            {/* Constraints */}
            {currentProblem?.constraints && (
              <div style={{marginTop: "12px"}}>
                <div style={{fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text2)", marginBottom: "4px"}}>Constraints</div>
                <ul style={{paddingLeft: "16px", margin: 0, fontSize: "12px", color: "var(--text2)"}}>
                  {(() => {
                    let cons = currentProblem.constraints;
                    if (typeof cons === 'string') {
                      try { cons = JSON.parse(cons); } catch(e) { cons = []; }
                    }
                    return Array.isArray(cons) ? cons.map((c, i) => <li key={i}>{c}</li>) : null;
                  })()}
                </ul>
              </div>
            )}

            {/* Examples */}
            {currentProblem?.examples && (
              <div style={{marginTop: "14px", display: "flex", flexDirection: "column", gap: "8px"}}>
                {(() => {
                  let ex = currentProblem.examples;
                  if (typeof ex === 'string') {
                    try { ex = JSON.parse(ex); } catch(e) { ex = []; }
                  }
                  return Array.isArray(ex) ? ex.map((e, idx) => (
                    <div key={idx} style={{
                      background: "rgba(0,0,0,0.3)", 
                      border: "1px solid var(--border)", 
                      borderRadius: "10px", 
                      padding: "8px 12px", 
                      fontFamily: "'DM Mono',monospace", 
                      fontSize: "11px", 
                      color: "var(--cyan)"
                    }}>
                      <strong>Example {idx + 1}:</strong><br/>
                      Input: {e.input}<br/>
                      Output: {e.output}<br/>
                      {e.explanation && <span style={{color: "var(--text3)"}}>Explanation: {e.explanation}</span>}
                    </div>
                  )) : null;
                })()}
              </div>
            )}

            <div style={{marginTop:"auto", paddingTop: "20px"}}>
              <div className="sec-sub fw7 mb8">AI Hints</div>
              <div className="hint-box" style={{color: hintBox.startsWith('Getting') ? 'var(--text2)' : '#b0c0d8'}}>{hintBox}</div>
              <button className="btn btn-ghost btn-sm" style={{width:"100%", justifyContent:"center", marginTop:"8px"}} onClick={getHint}>💡 Get AI Hint</button>
            </div>
          </div>

          {/* Right panel: Code editor, runner outcome */}
          <div className="flex-col gap10">
            <div className="flex items-center" style={{justifyContent:"space-between"}}>
              <select 
                className="lang-select" 
                style={{ backgroundColor: "#0c1220", color: "#f0f4fd" }}
                value={lang} 
                onChange={(e) => handleLangChange(e.target.value)} 
                aria-label="Select programming language"
              >
                <option value="python" style={{ background: "#0c1220", color: "#f0f4fd" }}>Python</option>
                <option value="javascript" style={{ background: "#0c1220", color: "#f0f4fd" }}>JavaScript</option>
                <option value="typescript" style={{ background: "#0c1220", color: "#f0f4fd" }}>TypeScript</option>
                <option value="java" style={{ background: "#0c1220", color: "#f0f4fd" }}>Java</option>
                <option value="cpp" style={{ background: "#0c1220", color: "#f0f4fd" }}>C++</option>
                <option value="csharp" style={{ background: "#0c1220", color: "#f0f4fd" }}>C#</option>
                <option value="go" style={{ background: "#0c1220", color: "#f0f4fd" }}>Go</option>
                <option value="rust" style={{ background: "#0c1220", color: "#f0f4fd" }}>Rust</option>
                <option value="php" style={{ background: "#0c1220", color: "#f0f4fd" }}>PHP</option>
                <option value="ruby" style={{ background: "#0c1220", color: "#f0f4fd" }}>Ruby</option>
                <option value="swift" style={{ background: "#0c1220", color: "#f0f4fd" }}>Swift</option>
                <option value="kotlin" style={{ background: "#0c1220", color: "#f0f4fd" }}>Kotlin</option>
                <option value="sql" style={{ background: "#0c1220", color: "#f0f4fd" }}>SQL</option>
              </select>
              <div className="flex gap8" style={{ alignItems: "center", flexWrap: "wrap" }}>
                {roomId && <span className="pill pill-cyan" style={{ fontSize: "11px", fontWeight: 800 }}>👥 {Math.max(1, roomParticipants.length)} Participant{roomParticipants.length === 1 ? '' : 's'} Active</span>}
                {roomId && <span className="pill pill-purple" style={{ fontSize: "11px", fontWeight: 800 }}>🖥️ Room Sync Active</span>}
                <button className="btn btn-ghost btn-sm" onClick={resetStarterCode}>Reset Starter</button>
                <button className="btn btn-primary btn-sm" onClick={runCode}>▶ Run Code</button>
              </div>
            </div>
            
            <SmartCodeEditor 
              value={code} 
              onChange={handleCodeChange} 
              lang={lang} 
              isRoomActive={Boolean(roomId)} 
              participants={roomParticipants} 
              currentUserId={user?._id || user?.user_id || user?.id || localStorage.getItem("user_id")} 
            />
            
            {/* Console execution outputs */}
            <div>
              <div className="sec-sub fw7 mb8">Console Output</div>
              <div className="console-out" id="console-out" style={{
                color: consoleColor, 
                whiteSpace: "pre-wrap", 
                maxHeight: "140px", 
                overflowY: "auto",
                fontFamily: "'DM Mono', monospace",
                fontSize: "12px"
              }} aria-live="polite">
                {consoleOut}
              </div>
            </div>
            
            {/* Detailed Test Cases Outcome */}
            {testCaseResults && testCaseResults.length > 0 && (
              <div className="card-sm" style={{
                background: "rgba(255,255,255,0.01)",
                borderColor: "rgba(255,255,255,0.05)",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                maxHeight: "180px",
                overflowY: "auto",
                padding: "14px 18px",
                marginTop: "4px"
              }}>
                {/* Sample Tests */}
                {testCaseResults.some(tc => !tc.is_hidden) && (
                  <div>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--cyan)", textTransform: "uppercase", marginBottom: "8px", letterSpacing: "0.5px" }}>Sample Tests</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {testCaseResults.filter(tc => !tc.is_hidden).map((tc, idx) => (
                        <div key={`sample-${idx}`} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#b0c0d8" }}>
                          <span style={{ color: tc.passed ? "#00d68f" : "var(--red)", fontWeight: "bold" }}>{tc.passed ? "✔" : "✘"}</span>
                          <span>Test Case {idx + 1}</span>
                          <span style={{ marginLeft: "auto", fontSize: "10px", color: "var(--text3)" }}>
                            {tc.passed ? `Passed [${tc.time_ms ? tc.time_ms.toFixed(1) : 0}ms]` : "Failed"}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Hidden Tests */}
                {testCaseResults.some(tc => tc.is_hidden) && (
                  <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "10px", marginTop: "4px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 800, color: "var(--purple)", textTransform: "uppercase", marginBottom: "8px", letterSpacing: "0.5px" }}>Hidden Tests</div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#b0c0d8" }}>
                      <span style={{ 
                        color: testCaseResults.filter(tc => tc.is_hidden).every(tc => tc.passed) ? "#00d68f" : "var(--red)", 
                        fontWeight: "bold" 
                      }}>
                        {testCaseResults.filter(tc => tc.is_hidden).every(tc => tc.passed) ? "✔" : "✘"}
                      </span>
                      <span>
                        {testCaseResults.filter(tc => tc.is_hidden && tc.passed).length} / {testCaseResults.filter(tc => tc.is_hidden).length} Hidden Tests Passed
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* AI Review Tab */}
            <div className="card-sm" style={{background:"rgba(0,240,200,0.03)", borderColor:"rgba(0,240,200,0.13)", flex: 1, overflowY: "auto", maxHeight: "180px"}}>
              <div className="sec-sub fw7 mb8">AI Code Review</div>
              <div id="ai-review" className="text-sm" style={{color:"#b0c0d8", lineHeight:"1.6", whiteSpace: "pre-wrap"}}>
                {renderMarkdown(aiReview)}
              </div>
            </div>

            {/* Complexity and test indicators */}
            <div className="flex gap8">
              <div className="complexity-badge"><div className="cb-lbl">Time Complexity</div><div className="cb-val" style={{color:"var(--cyan)"}}>{timeComplexity}</div></div>
              <div className="complexity-badge"><div className="cb-lbl">Space Complexity</div><div className="cb-val" style={{color:"var(--blue)"}}>{spaceComplexity}</div></div>
              <div className="complexity-badge"><div className="cb-lbl">Test Cases Passed</div><div className="cb-val" style={{color: testPassColor}}>{testPass}</div></div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
