import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { NAV_GROUPS, NAV_ITEMS } from "@/lib/nav";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();

  const go = (path: string) => {
    onOpenChange(false);
    navigate(path);
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Command Palette" description="Jump to any module">
      <CommandInput placeholder="Search modules, pages, actions..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {NAV_GROUPS.map((group) => (
          <CommandGroup key={group} heading={group}>
            {NAV_ITEMS.filter((item) => item.group === group).map((item) => (
              <CommandItem key={item.path} value={`${item.label} ${item.description}`} onSelect={() => go(item.path)}>
                <item.icon className="size-4" />
                <span>{item.label}</span>
                <span className="ml-auto text-xs text-muted-foreground">{item.description}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
