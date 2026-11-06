//go:build !windows

package kingai

import "os/exec"

func configureProcess(cmd *exec.Cmd){}
