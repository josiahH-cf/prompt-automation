on run
    try
        do shell script "prompt-automation --gui &"
    on error
        try
            do shell script "prompt-automation --terminal &"
        on error
            display dialog "prompt-automation failed to start. Please check installation." buttons {"OK"} default button "OK"
        end try
    end try
end run
