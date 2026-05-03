import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { 
  Bold, 
  Italic, 
  List, 
  ListOrdered, 
  Quote, 
  Undo, 
  Redo 
} from 'lucide-react';

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function Editor({ value, onChange, placeholder }: EditorProps) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: value,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'prose prose-invert max-w-none min-h-[150px] focus:outline-none p-4 text-slate-300',
      },
    },
  });

  if (!editor) return null;

  return (
    <div className="border border-slate-800 rounded-2xl overflow-hidden bg-slate-900/50 backdrop-blur-sm focus-within:ring-2 focus-within:ring-indigo-600/20 transition-all">
      {/* Toolbar */}
      <div className="flex items-center gap-1 p-2 border-b border-slate-800 bg-slate-800/30">
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleBold().run()} 
          active={editor.isActive('bold')}
          icon={<Bold className="w-4 h-4" />}
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleItalic().run()} 
          active={editor.isActive('italic')}
          icon={<Italic className="w-4 h-4" />}
        />
        <div className="w-px h-4 bg-slate-700 mx-1" />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleBulletList().run()} 
          active={editor.isActive('bulletList')}
          icon={<List className="w-4 h-4" />}
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleOrderedList().run()} 
          active={editor.isActive('orderedList')}
          icon={<ListOrdered className="w-4 h-4" />}
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().toggleBlockquote().run()} 
          active={editor.isActive('blockquote')}
          icon={<Quote className="w-4 h-4" />}
        />
        <div className="flex-grow" />
        <ToolbarButton 
          onClick={() => editor.chain().focus().undo().run()} 
          icon={<Undo className="w-4 h-4" />}
        />
        <ToolbarButton 
          onClick={() => editor.chain().focus().redo().run()} 
          icon={<Redo className="w-4 h-4" />}
        />
      </div>

      <EditorContent editor={editor} />
    </div>
  );
}

function ToolbarButton({ onClick, active = false, icon }: { onClick: () => void, active?: boolean, icon: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`p-2 rounded-lg transition-colors ${
        active ? 'bg-indigo-600/20 text-indigo-400' : 'text-slate-500 hover:text-slate-200 hover:bg-slate-700/50'
      }`}
    >
      {icon}
    </button>
  );
}
