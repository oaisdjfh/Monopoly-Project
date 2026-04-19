def oled_big_text(controller_num, text, x = 0, y = 0, a =1, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.text_wrapped(text, x, y, a)
        except IndexError:
            None
    if controller_num == 2 or all:
        try:    
            if not player_list[1].ai:
                oled_big2.text_wrapped(text, x, y, a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.text_wrapped(text, x, y, a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.text_wrapped(text, x, y, a)
        except IndexError:
            None
def oled_big_rect(controller_num, text, x = 0, y = 0, w = 10, h = 10, a = 1, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.rect(text, x, y, w, h, a)
        except IndexError:
            None
    if controller_num == 2 or all:
        try:    
            if not player_list[1].ai:
                oled_big2.rect(text, x, y, w, h, a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.rect(text, x, y, w, h, a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.rect(text, x, y, w, h, a)
        except IndexError:
            None
def oled_big_show(controller_num, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.show()
        except IndexError:
            None
    if controller_num == 2 or all:
        try:    
            if not player_list[1].ai:
                oled_big2.show()
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.show()
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.show()
        except IndexError:
            None
def oled_big_fill(controller_num, a = 0, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled_big1.fill(a)
        except IndexError:
            None
    if controller_num == 2 or all:
        try:    
            if not player_list[1].ai:
                oled_big2.fill(a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled_big3.fill(a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled_big4.fill(a)
        except IndexError:
            None
def oled_text(controller_num, text, x = 0, y = 0, a = 1, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled1.text(text, x, y, a)
        except IndexError:
            None
    if controller_num == 2 or all:
        try:    
            if not player_list[1].ai:
                oled2.text(text, x, y, a)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled3.text(text, x, y, a)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled4.text(text, x, y, a)
        except IndexError:
            None
def oled_show(controller_num, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled1.show()
        except IndexError:
            None
    if controller_num == 2 or all:
        try:    
            if not player_list[1].ai:
                oled2.show()
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled3.show()
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled4.show()
        except IndexError:
            None
def oled_fill(controller_num, a = 0, all = False, true_clear = False):
    
    if true_clear:
        if controller_num == 1 or all:
            try:    
                if not player_list[0].ai:
                    oled1.fill(a)
            except IndexError:
                None
        if controller_num == 2 or all:
            try:    
                if not player_list[1].ai:
                    oled2.fill(a)
            except IndexError:
                None
        if controller_num == 3 or all:
            try:    
                if not player_list[2].ai:
                    oled3.fill(a)
            except IndexError:
                None
        if controller_num == 4 or all:
            try:    
                if not player_list[3].ai:
                    oled4.fill(a)  
            except IndexError:
                None
    else:
        if controller_num == 1 or all:
            try:    
                if not player_list[0].ai:
                    oled1.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
        if controller_num == 2 or all:
            try:    
                if not player_list[1].ai:
                    oled2.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
        if controller_num == 3 or all:
            try:    
                if not player_list[2].ai:
                    oled3.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
        if controller_num == 4 or all:
            try:    
                if not player_list[3].ai:
                    oled4.rect(0,15, 128, 60, 0, True)
            except IndexError:
                None
def oled_rect(controller_num, x, y, w, h, a = 1, fill = True, all = False):
    if controller_num == 1 or all:
        try:    
            if not player_list[0].ai:
                oled1.rect(x, y, w, h, a, fill)
        except IndexError:
            None
    if controller_num == 2 or all:
        try:    
            if not player_list[1].ai:
                oled2.rect(x, y, w, h, a, fill)
        except IndexError:
            None
    if controller_num == 3 or all:
        try:    
            if not player_list[2].ai:
                oled3.rect(x, y, w, h, a, fill)
        except IndexError:
            None
    if controller_num == 4 or all:
        try:    
            if not player_list[3].ai:
                oled4.rect(x, y, w, h, a, fill)
        except IndexError:
            None
def pcf_pin(pcf_num, color):
    if pcf_num == 1:
        try:    
            if not player_list[0].ai:
                return pcf1.pin(color)
        except IndexError:
            None
    if pcf_num == 2:
        try:    
            if not player_list[1].ai:
                return pcf2.pin(color)
        except IndexError:
            None
    if pcf_num == 3:
        try:    
            if not player_list[2].ai:
                return pcf3.pin(color)
        except IndexError:
            None
    if pcf_num == 4:
        try:    
            if not player_list[3].ai:
                        return pcf4.pin(color)
        except IndexError:
            None
                